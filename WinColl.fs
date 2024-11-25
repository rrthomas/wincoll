\ WinColl
\ Roughly equivalent to Repton 0.5

ONLY FORTH DEFINITIONS  DECIMAL
MARKER WINCOLL

\ Utility words
\ The argument to KEY? is the absolute value of the negative INKEY code.
: KEY?   ( c -- f )   256 >-<  255 SWAP  129 [ 3 3 ] OS" OS_Byte"  2DROP 255 = ;
: OFF   [ 0 0 ] OS" OS_RemoveCursors" ;

\ Monotonic timer
CREATE TIME-BUFFER  5 ALLOT
: @TIME   ( -- u )   TIME-BUFFER 1 [ 2 0 ] OS" OS_Word"  TIME-BUFFER @ ;
: !TIME   ( u -- )   TIME-BUFFER  TUCK !  2 [ 2 0 ] OS" OS_Word" ;

: DELAY   ( n -- )   @TIME  BEGIN @TIME OVER -  2 PICK < WHILE  REPEAT 2DROP ;

\ Graphics utilities
: RGB-EMIT  ROT EMIT  SWAP EMIT  EMIT ;
: COLOUR   17 EMIT   EMIT ;
: RGB  19 EMIT  EMIT  16 EMIT  RGB-EMIT ;
: BORDER  19 EMIT  255 EMIT  16 EMIT  RGB-EMIT ;

: WAIT   19 [ 1 0 ] OS" OS_Byte" ;
: MODE   ( u -- )   22 EMIT  EMIT ;
: SHADOW    ( draw to shadow bank )  2 [ 2 0 ] 112 OS" OS_Byte" ;
: DISPLAY-BANK   255 0 251 [ 3 2 ] OS" OS_Byte" DROP ;
: FLIP   ( swap screen banks )
   DISPLAY-BANK  DUP 2 >-< 113 [ 2 0 ] OS" OS_Byte"  112 [ 2 0 ] OS" OS_Byte" ;

: SPRITE   ( x y -- ) SWAP 237 [ 3 0 ] OS" OS_Plot" ;

: SPRITEN   ( n -- )
   0 <# BL HOLD  #S #> DROP  \ format number as blank-delimited string, keep only the address
   0    \ ignored
   24   \ OS_SpriteOp code
   [ 3 0 ] OS" OS_SpriteOp" ;

\ Initialise miscellaneous variables
0 CONSTANT Gap    1 CONSTANT Blob   2 CONSTANT Diamond
3 CONSTANT Key    4 CONSTANT Rock   5 CONSTANT Earth
6 CONSTANT Brick  7 CONSTANT Safe
100 CONSTANT Win  200 CONSTANT Splat
VARIABLE X  VARIABLE Y   ( your coordinates )  0 X ! 0 Y !
VARIABLE LIVES  VARIABLE DEAD?
VARIABLE LEVEL  4 CONSTANT LEVELS
VARIABLE DIAMONDS   \ number of diamonds left on level
50 CONSTANT LONG   \ length of side of world in blocks
LONG LONG *  CONSTANT AREA   \ of world array
CREATE WORLD   \ world array
AREA ALLOT
AREA WORLD + 1+ CONSTANT ENDWORLD   \ end of array
CREATE ORIGINAL   \ permanent array, WORLD used during game
AREA LEVELS * CONSTANT WORLDS-BYTES
WORLDS-BYTES ALLOT

\ Set up screen and handle sound
: PALETTE   \ set up screen palette
   255 255   0  2 RGB    0 255   0  3 RGB    0   0 200  4 RGB
   144 176 176  9 RGB  240 176 112 10 RGB  192 144  64 11 RGB
   144  80   0 12 RGB   48 128   0 13 RGB  128   0 128 14 RGB
   224 178 224 15 RGB    0   0 255  0 RGB    0   0   0  8 RGB
     0   0 255  BORDER ;
: .LOGO   \ set up the sprite banner
   *" SChoose Centre"  440 654 SPRITE ;
: SOUND   \ handle sound on/off
   17 KEY? IF *" VOLUME 1  " THEN
   82 KEY? IF *" VOLUME 100" THEN ;

\ Display world
64 CONSTANT SIZE   \ of sprites
0 CONSTANT WX  0 CONSTANT WY   \ base world coords
200 CONSTANT OX  50 CONSTANT OY   \ graphics coords of window
: XY>MEM   ( x y -- addr )
   LONG *  +  WORLD + ;
: XY>SCR   ( x y -- x' y' )
   SIZE * SWAP SIZE * OX + SWAP OY + ;
13 CONSTANT WINDOW-SIZE
: .WORLD   ( x y -- )
   LONG WINDOW-SIZE - SWAP 0 MAX MIN TO WY  LONG WINDOW-SIZE - SWAP 0 MAX MIN TO WX
   WINDOW-SIZE 0 DO  WINDOW-SIZE 0 DO
      J WX + I WY +  XY>MEM C@   DUP Win < IF  LEVEL @ 10 * + SPRITEN
      J I XY>SCR SPRITE  ELSE DROP THEN
   LOOP  LOOP ;

\ Status display
: .DIAMONDS   22 1 AT-XY  7 COLOUR  ." Diamonds: " DIAMONDS ? ;
: .LIVES   2 1 AT-XY  7 COLOUR  ."    Lives: " LIVES ? ;
: .LEVEL   22 3 AT-XY  7 COLOUR  ."    Level: " LEVEL ? ;
: .STATUS   .DIAMONDS .LIVES .LEVEL ;


\ Move rocks
1 CONSTANT X+
: DOWN?   LONG - C@ Gap = ;
: SIDEWAYS?   X+ NEGATE TO X+  X+ + DUP
   LONG - C@ SWAP C@ + 0= IF TRUE ELSE FALSE THEN ;
: FALL   \ make rocks fall
   ENDWORLD WORLD DO
      I C@ Rock = IF
         I LONG - C@  Earth < IF
            I DOWN? IF
               LONG NEGATE
            ELSE I SIDEWAYS? IF
                  X+ LONG -
               ELSE I SIDEWAYS? IF
                     X+ LONG -
                  ELSE 0
                  THEN
               THEN
            THEN
            DUP IF
               DUP I + LONG - C@ Win = IF
                  TRUE DEAD? !
               THEN
               I + Rock SWAP C!  Gap I C! *" SOUND 2 65526 100 2"
            ELSE DROP
            THEN
         THEN
      THEN
   LOOP ;

\ Deal with Win's moves
: GO   ( move through gap )   TRUE ;
: DIG   ( through earth )   TRUE ;
: MUNCH   ( a diamond )   TRUE -1 DIAMONDS +!
   *" SOUND 1 65526 110 2" ;
: UNLOCK   ( the safes )   TRUE  ENDWORLD WORLD
   DO  I C@ Safe = IF Diamond I C! THEN  LOOP
   *" SOUND 1 65526 80 2" ;
: PUSH   ( rock )
   OVER 2* X @ + Y @ XY>MEM C@ Gap =  OVER 0=  AND IF OVER X @ + Y
   @ 2DUP  XY>MEM Gap SWAP C!  3 PICK  ROT + SWAP  XY>MEM Rock SWAP C!
   TRUE ELSE FALSE THEN ;
: MOVE?   ( dx dy x' y' -- moved? )
   CASE XY>MEM C@
     0 OF GO ENDOF
     2 OF MUNCH ENDOF
     3 OF UNLOCK ENDOF
     4 OF PUSH ENDOF
     5 OF DIG ENDOF
     >R  FALSE  R>
   ENDCASE ;

\ Move around the world
: DELTA   ( -- dx dy )
   67 KEY? NEGATE   98 KEY?  +
   80 KEY? NEGATE  105 KEY?  +
   2DUP + 1 AND  IF EXIT  ELSE 2DROP 0 0  THEN ;
: .WIN   ( print our hero )
   LEVEL @ Win + SPRITEN
   X @ WX - Y @ WY - XY>SCR SPRITE ;
: WALK
   Gap X @ Y @ XY>MEM C!
   DELTA
   2DUP Y @ + SWAP X @ + SWAP MOVE? IF
      Y +! X +!
      ELSE 2DROP
   THEN Win X @ Y @ XY>MEM C! ;

\ Die and finish a level
: DIE
   LEVEL @ Splat + SPRITEN
   *" SOUND 3 65521 100 20"
   X @ WX - Y @ WY - XY>SCR SPRITE
   -1 LIVES +!  FALSE DEAD? !  Gap X @ Y @ XY>MEM C!
   WAIT FLIP 100 DELAY ;
: SURVEY   ( count the diamonds on the level )
   0 DIAMONDS !  *" SOUND 1 65521 30 20"
   ENDWORLD WORLD DO
      I C@ DUP Diamond = SWAP Safe = OR IF 1 DIAMONDS +! THEN
   LOOP ;
: FINISH   ( a level )
   1 LEVEL +!  WAIT FLIP
   ORIGINAL AREA LEVEL @ * + WORLD AREA CMOVE  SURVEY ;

\ Finish the whole game; die, live, or cheat
: SPLURGE   ( sprite# -- )
   0 TO WX  0 TO WY
   WINDOW-SIZE 0 DO  WINDOW-SIZE 0 DO
      DUP SPRITEN  I J XY>SCR SPRITE
   LOOP LOOP
   WAIT FLIP  300 DELAY ;
0 CONSTANT BEGINNING   3 CONSTANT INITIAL-LIVES
: CHEAT   ( change start level )
        DUP 48 = IF 0 TO BEGINNING THEN
        DUP 49 = IF 1 TO BEGINNING THEN
        DUP 50 = IF 2 TO BEGINNING THEN
        DUP 51 = IF 3 TO BEGINNING THEN
   DUP [CHAR] + = IF INITIAL-LIVES 1+ 10 MIN TO INITIAL-LIVES  THEN
   DUP [CHAR] - = IF INITIAL-LIVES 1-  0 MAX TO INITIAL-LIVES  THEN ;

\ Play the game!
: PLAY
   9 MODE OFF PALETTE SHADOW
   INITIAL-LIVES LIVES ! BEGINNING LEVEL ! 0 DEAD? !  0 !TIME
   ORIGINAL AREA LEVEL @ * + WORLD AREA CMOVE  SURVEY
   1 X ! 1 Y ! 0 0 .WORLD .WIN .STATUS  WAIT FLIP
   BEGIN  0 !TIME 1 X ! 1 Y !  0 0 .WORLD .WIN .STATUS
      BEGIN
         56 KEY? IF @TIME BEGIN 52 KEY? UNTIL !TIME THEN
         WAIT FLIP  WALK FALL   10 DELAY \ FIXME constant frame rate
         36 KEY? IF TRUE DEAD? ! THEN
         X @ WINDOW-SIZE 2/ -  Y @ WINDOW-SIZE 2/ -  .WORLD
         .WIN .STATUS  SOUND
      DEAD? @ DIAMONDS @ 0= OR UNTIL
   DEAD? @ IF DIE ELSE FINISH THEN
   LIVES @ 0= LEVEL @ LEVELS = OR UNTIL  .STATUS
   LIVES @ 0= IF Splat SPLURGE ELSE Win SPLURGE THEN ;

\ Instructions
: INSTRUCT   9 MODE OFF PALETTE  7 COLOUR  0 14 AT-XY  .LOGO
   ."  This game is an unashamed Repton clone,"
   ." with sprites and screens designed by"     CR
   ." Pav, Jes, Al, and Roobs, who also "       CR
   ." programmed it."                           CR
   ."  This version does not have eggs. It has"
   ." round bricks instead. Apart from that,"   CR
   ." it is almost the same as Repton 1."       CR
                                                CR
   ."     Z/X - Left/Right   '/? - Up/Down"     CR
   ." S/Q - Sound on/off  P/R - Pause/Unpause"  CR
   ."            T  - Terminate life"           CR CR
   CR ."      Press the space bar to enjoy!      "
   BEGIN KEY CHEAT 32 = UNTIL ;

\ Load world, sprites and sound module
: @DATA   ( load data )
   ORIGINAL WORLDS-BYTES
   S" Data" R/O OPEN-FILE  DROP   \ FIXME: check ior code
   READ-FILE
   2DROP   \ FIXME: check ior code and number of bytes
   ;
: *COMMANDS   ( load files )
   *" SLoad WinSpr"
   *" RMLoad UserVoices"  *" ChannelVoice 1 Ping"
   *" ChannelVoice 2 Slide"  *" Volume 100"
   *" ChannelVoice 3 Bash" ;

\ Main loop
: ENJOY
   @DATA *COMMANDS
   BEGIN
      *" FX15"
      INSTRUCT PLAY
   AGAIN ;

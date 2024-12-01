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

: DELAY   ( n -- )   @TIME  BEGIN @TIME OVER -  2 PICK < WHILE  REPEAT 2DROP ;

\ Graphics utilities
: RGB-EMIT  ROT EMIT  SWAP EMIT  EMIT ;
: COLOUR   17 EMIT   EMIT ;
: RGB  19 EMIT  EMIT  16 EMIT  RGB-EMIT ;

: CLS   12 EMIT ;
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
VARIABLE DEAD?
VARIABLE LEVEL  16 CONSTANT LEVELS
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
     0   0 200  8 RGB  144 176 176  9 RGB  240 176 112 10 RGB
   192 144  64 11 RGB  144  80   0 12 RGB   48 128   0 13 RGB
   224 178 224 15 RGB ;
: .LOGO   \ set up the sprite banner
   *" SChoose Centre"  440 654 SPRITE ;

\ Display world
64 CONSTANT SIZE   \ of sprites
0 CONSTANT WX  0 CONSTANT WY   \ base world coords
160 CONSTANT OX  16 CONSTANT OY   \ graphics coords of window
: XY>MEM   ( x y -- addr )
   LONG *  +  WORLD + ;
: XY>SCR   ( x y -- x' y' )
   SIZE * SWAP SIZE * OX + SWAP OY + ;
15 CONSTANT WINDOW-SIZE
: .WORLD   ( x y -- )
   LONG WINDOW-SIZE - SWAP 0 MAX MIN TO WY  LONG WINDOW-SIZE - SWAP 0 MAX MIN TO WX
   WINDOW-SIZE 0 DO  WINDOW-SIZE 0 DO
      J WX + I WY +  XY>MEM C@ SPRITEN
      J I XY>SCR SPRITE
   LOOP  LOOP ;

\ Status display
: .DIAMONDS   23 0 AT-XY  7 COLOUR  ." Diamonds: " DIAMONDS ? ;
: .LEVEL   1 0 AT-XY  7 COLOUR  ." Level: " LEVEL @ 1+ . ;
: .STATUS   .DIAMONDS .LEVEL ;

\ Load and save data
: LOAD-DATA R/O OPEN-FILE  DROP   \ FIXME: check ior code
   DUP >R  READ-FILE 2DROP
   R> CLOSE-FILE DROP ;  \ FIXME: check ior code and number of bytes
: SAVE-DATA R/W CREATE-FILE  DROP   \ FIXME: check ior code
   DUP >R  WRITE-FILE 2DROP
   R> CLOSE-FILE DROP ;  \ FIXME: check ior code and number of bytes

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
: WALK
   Gap X @ Y @ XY>MEM C!
   DELTA
   2DUP Y @ + SWAP X @ + SWAP MOVE? IF
      Y +! X +!
      ELSE 2DROP
   THEN Win X @ Y @ XY>MEM C! ;

\ Die and finish a level
: DIE
   Splat SPRITEN
   *" SOUND 3 65521 100 20"
   X @ WX - Y @ WY - XY>SCR SPRITE
   FALSE DEAD? !  Gap X @ Y @ XY>MEM C!
   WAIT FLIP 100 DELAY ;
: SURVEY   ( count the diamonds on the level )
   0 DIAMONDS !  *" SOUND 1 65521 30 20"
   ENDWORLD WORLD DO
      I C@ DUP Diamond = SWAP Safe = OR IF 1 DIAMONDS +! THEN
      I C@ Win = IF  I WORLD -  LONG U/MOD  Y ! X !  THEN
   LOOP ;
: FINISH   ( a level )
   1 LEVEL +!  WAIT FLIP
   ORIGINAL AREA LEVEL @ * + WORLD AREA CMOVE  SURVEY ;

\ Load and save current position
: LOAD-POSITION   WORLD AREA S" Saved" LOAD-DATA  SURVEY ;
: SAVE-POSITION   WORLD AREA S" Saved" SAVE-DATA ;

\ Finish the whole game; die, live, or cheat
: SPLURGE   ( sprite# -- )
   0 TO WX  0 TO WY
   WINDOW-SIZE 0 DO  WINDOW-SIZE 0 DO
      DUP SPRITEN  I J XY>SCR SPRITE
   LOOP LOOP
   WAIT FLIP  300 DELAY ;

\ Play the game!
: INIT-SCREEN   9 MODE OFF 132 COLOUR CLS PALETTE ;

: RESET-POSITION   1 X ! 1 Y ! ;
: RESTART-LEVEL   ORIGINAL AREA LEVEL @ * + WORLD AREA CMOVE  SURVEY
   RESET-POSITION ;

: PLAY   ( start-level -- )
   INIT-SCREEN SHADOW
   1- LEVEL ! 0 DEAD? !
   RESTART-LEVEL  0 0 .WORLD .STATUS  WAIT FLIP
   BEGIN  RESET-POSITION  0 0 .WORLD .STATUS
      BEGIN
         @TIME 10 +
         WAIT FLIP  WALK FALL
         87 KEY? IF LOAD-POSITION ELSE 82 KEY? IF SAVE-POSITION THEN THEN
         52 KEY? IF RESTART-LEVEL THEN
         17 KEY? IF ABORT" Game over!" THEN \ FIXME: Make this nicer!
         X @ WINDOW-SIZE 2/ -  Y @ WINDOW-SIZE 2/ -  .WORLD
         .STATUS
         BEGIN @TIME OVER - 0> UNTIL  DROP
      DEAD? @ DIAMONDS @ 0= OR UNTIL
   DEAD? @ IF DIE ELSE FINISH THEN
   LEVEL @ LEVELS = UNTIL  .STATUS
   Win SPLURGE ;

\ Instructions
: INSTRUCT   ( -- start-level )
   INIT-SCREEN  7 COLOUR  0 14 AT-XY  .LOGO
   ."  This game is an unashamed Repton clone,"
   ." with sprites and screens designed by"     CR
   ." Pav, Jes, Al, and Roobs, who also "       CR
   ." programmed it."                           CR
   ."  This version does not have eggs. It has"
   ." round bricks instead. Apart from that,"   CR
   ." it is almost the same as Repton 1."       CR
                                                CR
   ."     Z/X - Left/Right   '/? - Up/Down"     CR
   ."         S/L - Save/load position"         CR
   ."       R - Restart level  Q - Quit game"   CR
   ."     Type level number to select level"    CR CR
   CR ."      Press the space bar to enjoy!      "
   0   \ Accumulator for start level
   BEGIN
      KEY
      DUP [CHAR] 0 [CHAR] 9 1+ WITHIN IF
         \ If char is 0 to 9, add a digit to level number
         DUP [CHAR] 0 -
         ROT 10 * +  SWAP
      ELSE
         DUP BL <> IF  NIP  0 SWAP THEN   \ Else if not space, reset to 0
      THEN
   BL = UNTIL
   DUP 0= IF DROP 1 THEN
   LEVELS MIN ;

\ Load world, sprites and sound module
: @DATA   ( load data )   ORIGINAL WORLDS-BYTES S" Data" LOAD-DATA ;

\ Main loop
: ENJOY
   @DATA
   BEGIN
      *" FX15"
      INSTRUCT PLAY
   AGAIN ;

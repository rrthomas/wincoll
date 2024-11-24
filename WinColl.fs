\ WinColl
\ Roughly equivalent to Repton 0.5
\ need to fix: SPRITE (plot current sprite at given position),
\              SPRITEN (*Schoose sprite N), @DATA (use OS_GBPB)

ONLY FORTH DEFINITIONS  DECIMAL
MARKER WINCOLL

\ Utility words
: KEY?   ( c -- f )   256 >-<  255 129 [ 3 ] OS_Byte  2DROP 255 = ;

\ Initialise miscellaneous variables
0 CONSTANT Gap    1 CONSTANT Blob   2 CONSTANT Diamond
3 CONSTANT Key    4 CONSTANT Rock   5 CONSTANT Earth
6 CONSTANT Brick  7 CONSTANT Safe
100 CONSTANT Win  200 CONSTANT Splat
VARIABLE X  VARIABLE Y   ( your coordinates )  0 X ! 0 Y !
VARIABLE SCORE  VARIABLE LIVES  VARIABLE DEAD?
VARIABLE LEVEL  4 CONSTANT LEVELS  50000 CONSTANT DURATION
VARIABLE DIAMONDS   \ number of diamonds left on level
50 CONSTANT LONG   \ length of side of world in blocks
LONG LONG *  CONSTANT AREA   \ of world array
CREATE WORLD   \ world array
AREA ALLOT
AREA WORLD + 1+ CONSTANT ENDWORLD   \ end of array
CREATE ORIGINAL   \ permanent array, WORLD used during game
AREA LEVELS * ALLOT

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
200 CONSTANT OX  151 CONSTANT OY   \ graphics coords of window
: XY>MEM   ( x y -- addr )
   LONG *  +  WORLD + ;
: XY>SCR   ( x y -- x' y' )
   SIZE * SWAP SIZE * OX + SWAP OY + ;
: .WORLD   ( x y -- )
   LONG 7 - SWAP 0 MAX MIN TO WY  LONG 7 - SWAP 0 MAX MIN TO WX
   7 0 DO  7 0 DO
      J WX + I WY +  XY>MEM C@ LEVEL @ 10 * + SPRITEN
      J I XY>SCR SPRITE
   LOOP  LOOP ;

\ Status display
: .SCORE   22 14 AT-XY  7 COLOUR  ."    Score: " SCORE ? ;
: .SANDS   22 16 AT-XY  7 COLOUR  ."     Time: "
   DURATION @TIME - 100 / 0 MAX . ;
: .DIAMONDS   22 18 AT-XY  7 COLOUR  ." Diamonds: " DIAMONDS ? ;
: .LIVES   22 20 AT-XY  7 COLOUR  ."    Lives: " LIVES ? ;
: .LEVEL   22 22 AT-XY  7 COLOUR  ."    Level: " LEVEL ? ;
: .STATUS   .SCORE .SANDS .DIAMONDS .LIVES .LEVEL ;


\ Move rocks
1 CONSTANT X+
: DOWN?   I LONG - C@ Gap = ;
: SIDEWAYS?   X+ NEGATE TO X+  I X+ + DUP
   LONG - C@ SWAP C@ + 0= IF TRUE ELSE FALSE THEN ;
: FALL   \ make rocks fall
   ENDWORLD WORLD DO
      I C@ Rock = IF
         I LONG - C@  Earth < IF @TIME 1 AND 1- 1 OR TO X+
         DOWN? IF LONG NEGATE
         ELSE SIDEWAYS? IF X+ LONG - ELSE SIDEWAYS? IF X+ LONG -
         ELSE 0 THEN THEN THEN
         DUP IF DUP I + LONG - C@ Win = IF TRUE DEAD? ! THEN
         I + Rock SWAP C!  Gap I C! *" SOUND 2 65526 100 2"
      ELSE DROP  THEN THEN THEN
   LOOP ;

\ Deal with Win's moves
: GO   ( move through gap )   TRUE ;
: DIG   ( through earth )   1 SCORE +!  TRUE ;
: MUNCH   ( a diamond )   10 SCORE +!  TRUE -1 DIAMONDS +!
*" SOUND 1 65526 110 2" ;
: UNLOCK   ( the safes )   5 SCORE +!  TRUE  ENDWORLD WORLD
DO  I C@ Safe = IF Diamond I C! THEN  LOOP
*" SOUND 1 65526 80 2" ;
: PUSH   ( rock/egg )
OVER 2* X @ + Y @ XY>MEM C@ Gap =  OVER 0=  AND IF OVER X @ + Y
@ 2DUP  XY>MEM Gap SWAP C!  3 PICK UNDER+ XY>MEM Rock SWAP C!
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
   ORIGINAL AREA LEVEL @ * + WORLD AREA CMOVE  SURVEY
   DURATION 25000 + TO DURATION ;

\ Finish the whole game; die, live, or cheat
: SPLURGE   ( sprite# -- )
   0 TO WX  0 TO WY
   7 0 DO  7 0 DO
      DUP SPRITEN  I J XY>SCR SPRITE
   LOOP LOOP
   WAIT FLIP  300 DELAY ;
0 CONSTANT BEGINNING   3 CONSTANT MEN
: CHEAT   ( change start level )
        DUP 48 = IF 0 TO BEGINNING THEN
        DUP 49 = IF 1 TO BEGINNING THEN
        DUP 50 = IF 2 TO BEGINNING THEN
        DUP 51 = IF 3 TO BEGINNING THEN
   DUP ASCII + = IF MEN 1+ 10 MIN TO MEN  THEN
   DUP ASCII - = IF MEN 1-  0 MAX TO MEN  THEN
   25000 BEGINNING * 50000 + TO DURATION ;

\ Play the game!
: PLAY
   9 MODE OFF PALETTE SHADOW
   0 SCORE ! MEN LIVES ! BEGINNING LEVEL ! 0 DEAD? !  0 !TIME
   ORIGINAL AREA LEVEL @ * + WORLD AREA CMOVE  SURVEY
   1 X ! 1 Y ! 0 0 .WORLD .WIN .LOGO .STATUS  WAIT FLIP
   BEGIN  0 !TIME 1 X ! 1 Y !  0 0 .WORLD .WIN .LOGO .STATUS
      BEGIN
         56 KEY? IF @TIME BEGIN 52 KEY? UNTIL !TIME THEN
         WAIT FLIP  WALK FALL
         @TIME DURATION > 36 KEY? OR IF TRUE DEAD? ! THEN
         X @ 3 - Y @ 3 - .WORLD .WIN .STATUS  SOUND
      DEAD? @ DIAMONDS @ 0= OR UNTIL
   DEAD? @ IF DIE ELSE FINISH THEN
   LIVES @ 0= LEVEL @ LEVELS = OR UNTIL  .STATUS
   LIVES @ 0= IF Splat SPLURGE ELSE Win SPLURGE THEN ;

\ Instructions
: INSTRUCT   9 MODE -CURSOR PALETTE  7 COLOUR  0 13 AT-XY  .LOGO
   ."  This game is an unashamed Repton clone,"
   ." with sprites and screens designed by"     CR
   ." Pav, Jes & Al, and programmed by Roobs"   CR
   ." in pForth."                               CR
   ."  This version does not have eggs. It has"
   ." round bricks instead. Apart from that,"   CR
   ." it is almost the same as Repton 1."       CR
   ."  If you have never played a Repton game,"
   ." then you should be ashamed of yourself!"  CR
                                                CR
   ."     Z/X - Left/Right   '/? - Up/Down"     CR
   ." S/Q - Sound on/off  P/R - Pause/Unpause"  CR
   ."            T  - Terminate life"           CR CR
   CR ."      Press the space bar to enjoy!      "
   BEGIN KEY CHEAT 32 = UNTIL ;

\ Load world, sprites and sound module
: @DATA   ( load data )   *" LOAD Data Original" ;
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

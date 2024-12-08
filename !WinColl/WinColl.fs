\ WinColl

\ Utility words
: INKEY   ( u -- c )  256 U/MOD SWAP  129 [ 3 3 ] OS" OS_Byte"
   DROP  SWAP 0<> IF  DROP -1 THEN
   126 [ 1 0 ] OS" XOS_Byte"   \ Clear any escape condition
   ;
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
   U>UD <# BL HOLD  #S #> DROP  \ format number as blank-delimited string, keep only the address
   0    \ ignored
   24   \ OS_SpriteOp code
   [ 3 0 ] OS" OS_SpriteOp" ;

\ Initialise miscellaneous variables
    BL CONSTANT Gap    CHAR + CONSTANT Blob   CHAR * CONSTANT Diamond
CHAR K CONSTANT Key    CHAR @ CONSTANT Rock   CHAR . CONSTANT Earth
CHAR # CONSTANT Brick  CHAR $ CONSTANT Safe
CHAR W CONSTANT Win       200 CONSTANT Splat
VARIABLE X  VARIABLE Y   ( your coordinates )
VARIABLE DEAD?
VARIABLE LEVEL  16 CONSTANT LEVELS
VARIABLE DIAMONDS   \ number of diamonds left on level
50 CONSTANT LONG   \ length of side of world in blocks
LONG 1+ CONSTANT ROW   \ length of data row in bytes
LONG ROW *  CONSTANT AREA   \ size of world array
CREATE WORLD   \ world array
AREA ALLOT
AREA WORLD + 1+ CONSTANT ENDWORLD   \ end of array

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
: XY>MEM   ( x y -- addr )   LONG 1- >-<  ROW *  +  WORLD + ;
: XY>SCR   ( x y -- x' y' )
   SIZE * SWAP SIZE * OX + SWAP OY + ;
15 CONSTANT WINDOW-SIZE
: .WORLD   ( x y -- )
   LONG WINDOW-SIZE - SWAP 0 MAX MIN TO WY
   LONG WINDOW-SIZE - SWAP 0 MAX MIN TO WX
   WINDOW-SIZE 0 DO  WINDOW-SIZE 0 DO
      J WX + I WY +  XY>MEM C@ SPRITEN
      J I XY>SCR SPRITE
   LOOP  LOOP ;

\ Status display
: .DIAMONDS   23 0 AT-XY  7 COLOUR  ." Diamonds: " DIAMONDS ? ;
: .LEVEL   1 0 AT-XY  7 COLOUR  ." Level: " LEVEL @ 1+ . ;
: .STATUS   .DIAMONDS .LEVEL ;

\ Load and save data
: LOAD-DATA R/O OPEN-FILE  DROP
   DUP >R  READ-FILE 2DROP
   R> CLOSE-FILE DROP ;
: SAVE-DATA R/W CREATE-FILE  DROP
   DUP >R  WRITE-FILE 2DROP
   R> CLOSE-FILE DROP ;

\ Move rocks
: DOWN?   ROW + C@ Gap = ;
: SIDEWAYS?   DUP  ROW + C@ Gap =  SWAP C@ Gap =  AND ;
: FALL  2DUP + ROW + C@ Win = IF  TRUE DEAD? !  THEN
   OVER + Rock SWAP C!  Gap SWAP C! *" SOUND 2 65526 100 2" ;
: ROCKS   \ make rocks fall
   WORLD ENDWORLD 1- DO
      I C@ Rock = IF
         I ROW + C@
         DUP Rock =  OVER Key = OR  OVER Diamond = OR
         OVER Blob = OR  SWAP Gap = OR IF
            I DOWN? IF
               I ROW FALL
            ELSE I 1- SIDEWAYS? IF
                  I ROW 1- FALL
               ELSE I 1+ SIDEWAYS? IF
                     I ROW 1+ FALL
                  THEN
               THEN
            THEN
         THEN
      THEN
   -1 +LOOP ;

\ Deal with Win's moves
: COLLECT   ( a diamond )   TRUE -1 DIAMONDS +!
   *" SOUND 1 65526 110 2" ;
: UNLOCK   ( the safes )   TRUE  ENDWORLD WORLD
   DO  I C@ Safe = IF Diamond I C! THEN  LOOP
   *" SOUND 1 65526 80 2" ;
: PUSH   ( rock )
   OVER 2* X @ + Y @ XY>MEM C@ Gap =  OVER 0=  AND IF
      OVER 2* X @ + Y @ XY>MEM Rock SWAP C!  TRUE
   ELSE FALSE THEN ;
: MOVE?   ( dx dy x' y' -- moved? )
   CASE XY>MEM C@
      Gap OF TRUE ENDOF
      Diamond OF COLLECT ENDOF
      Key OF UNLOCK ENDOF
      Rock OF PUSH ENDOF
      Earth OF TRUE ENDOF
      >R  FALSE  R>
   ENDCASE ;

\ Move around the world
: WALK   ( dx dy -- )
   Gap X @ Y @ XY>MEM C!
   2DUP Y @ + SWAP X @ + SWAP MOVE? IF
      Y +! X +!
      ELSE 2DROP
   THEN Win X @ Y @ XY>MEM C! ;

: DIE
   Splat SPRITEN
   *" SOUND 3 65521 100 20"
   X @ WX - Y @ WY - XY>SCR SPRITE
   FALSE DEAD? !
   WAIT FLIP 100 DELAY ;

: SURVEY   ( count the diamonds on the level )
   0 DIAMONDS !  *" SOUND 1 65521 30 20"
   ENDWORLD WORLD DO
      I C@ DUP Diamond = SWAP Safe = OR IF 1 DIAMONDS +! THEN
      I C@ Win = IF  I WORLD -  ROW U/MOD  LONG 1- >-< Y ! X !  THEN
   LOOP ;

CREATE DATA-FILE-NAME S" Level01" ",
: LEVEL#   U>UD <# # # #> ;
: @LEVEL   ( u --  )
   LEVEL#  DATA-FILE-NAME COUNT DROP
   5 + SWAP CMOVE   \ Copy level number into file name
   WORLD AREA DATA-FILE-NAME COUNT LOAD-DATA ;

\ Load and save current position
: LOAD-POSITION   WORLD AREA S" Saved" LOAD-DATA  SURVEY ;
: SAVE-POSITION   WORLD AREA S" Saved" SAVE-DATA ;

: RESET-POSITION   1 X ! 1 Y ! ;
: RESTART-LEVEL   LEVEL @ 1+ @LEVEL  RESET-POSITION SURVEY ;
: START-LEVEL   RESTART-LEVEL SAVE-POSITION ;

\ Fill the screen with one sprite
: SPLURGE   ( sprite# -- )
   WINDOW-SIZE 0 DO  WINDOW-SIZE 0 DO
      DUP SPRITEN  I J XY>SCR SPRITE
   LOOP LOOP
   WAIT FLIP  300 DELAY ;

\ Play the game!
: INIT-SCREEN   9 MODE OFF 132 COLOUR CLS PALETTE ;

10 CONSTANT FRAME-LENGTH
: FINISHED?   DIAMONDS @ 0= ;
: PLAY   ( start-level -- )
   INIT-SCREEN SHADOW  CLS WAIT FLIP
   1- LEVEL ! 0 DEAD? !
   BEGIN
      START-LEVEL
      BEGIN  LOAD-POSITION
         BEGIN
            @TIME FRAME-LENGTH +
            0 INKEY  *" FX 15"
            DUP [CHAR] x =  OVER [CHAR] X = OR  OVER 137 = OR IF
               1 0 WALK
            ELSE DUP [CHAR] z =  OVER [CHAR] Z = OR  OVER 136 = OR IF
               -1 0 WALK
            ELSE DUP [CHAR] ' =  OVER [CHAR] " = OR  OVER 139 = OR IF
               0 1 WALK
            ELSE DUP [CHAR] / =  OVER [CHAR] ? = OR  OVER 138 = OR IF
                  0 -1 WALK
            ELSE DUP [CHAR] l =  OVER [CHAR] L = OR IF LOAD-POSITION
            ELSE DUP [CHAR] s =  OVER [CHAR] S = OR IF SAVE-POSITION
            ELSE DUP [CHAR] r =  OVER [CHAR] R = OR IF RESTART-LEVEL
            ELSE DUP [CHAR] q =  OVER [CHAR] Q = OR IF DROP EXIT
            THEN THEN THEN THEN THEN THEN THEN THEN DROP
            ROCKS
            X @ WINDOW-SIZE 2/ -  Y @ WINDOW-SIZE 2/ -  .WORLD
            .STATUS
            WAIT FLIP
            BEGIN @TIME OVER - 0> UNTIL  DROP
         DEAD? @ FINISHED? OR UNTIL
         DEAD? @ IF DIE THEN
      FINISHED? UNTIL
      1 LEVEL +!
   LEVEL @ LEVELS = UNTIL
   Win SPLURGE ;

\ Instructions
: INSTRUCT   ( -- start-level )
   INIT-SCREEN  7 COLOUR  0 14 AT-XY  .LOGO
   ."  This game is an unashamed Repton clone,"
   ." with graphics and levels designed by"     CR
   ." Pav, Jes, Al, and Roobs, who also "       CR
   ." programmed it."                           CR
                                                CR
   ."     Z/X - Left/Right   '/? - Up/Down"     CR
   ."      or use the cursor keys to move"      CR
   ."         S/L - Save/load position"         CR
   ."       R - Restart level  Q - Quit game"   CR
   ."     Type level number to select level"    CR CR
   CR ."      Press the space bar to enjoy!      "
   0   \ Accumulator for start level
   BEGIN
      KEY
      DUP 27 = IF *" Quit" THEN
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

\ Main loop
: ENJOY
   FRAME-LENGTH 11 [ 2 0 ] OS" OS_Byte"
   FRAME-LENGTH 12 [ 2 0 ] OS" OS_Byte"
   *" FX 4,1"   \ Disable cursor editing, cursor keys return a character code
   BEGIN
      *" FX 15"
      INSTRUCT PLAY
   AGAIN ;

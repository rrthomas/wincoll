# WinColl for RISC OS

I wrote WinColl in Forth in 1989-90 with the proprietary RiscForth from BlueGrey software. In 2024 I resurrected it to work with the RISC OS version of my own [pForth](https://github.com/rrthomas/pforth/releases/tag/riscos) compiler, and then gave up and rewrote it in BBC BASIC.

The sound module `UserVoices` was generated using a program from [RISC User Volume 1 Issue 4](https://ia903207.us.archive.org/18/items/Risc_User_Volume_1_Issue_4_1988-03_BEEBUG_GB/). I no longer have the source code for my adaptation of the module, which uses different sound data from the examples given in the magazine; reconstructing it would certainly be possible, though! Get in touch if you’re interested. One motivation is that the module seems to have a bug where it cannot be finalised.


## Installation and use

* Download and unpack the
  [Zip](https://github.com/rrthomas/wincoll/archive/refs/heads/main.zip) of
  the WinColl Git repository.
* Launch `!WinColl` (for example, by double left-clicking it).

WinColl should run on RISC OS 3.5 to 3.7, and could probably be made to run on RISC OS 2 without difficulty.

The RISC OS version comes with its own level editor. If you would like to submit levels for inclusion in the official release, you will need to convert them to Tiled format, using the `level2tiled` script.


## Classic version

For historical interest, the [original game](https://github.com/rrthomas/wincoll/tree/classic) is also available, with the minimal updates required to make it run on pForth.

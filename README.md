# WinColl

https://github.com/rrthomas/wincoll  

by Reuben Thomas <rrt@sc3d.org>  

WinColl is a simple
[Repton](https://en.wikipedia.org/wiki/Repton_(video_game)) clone, written
in Forth for RISC OS in 1990.

It requires [pForth](https://github.com/rrthomas/pforth) to run. You will
need the latest
[RISC OS version](https://github.com/rrthomas/pforth/releases/tag/riscos).


## Installation and use

* Download and unpack the [Zip](https://github.com/rrthomas/wincoll/archive/refs/heads/main.zip) of the WinColl Git repository. Name the directory `!WinColl`.
+ Download and unpack the [Zip](https://github.com/rrthomas/pforth/archive/refs/tags/riscos.zip) of RISC OS pForth.
* Copy the RISC OS application `src/!pForth` to a suitable location; for example, the same directory as that containing `!WinColl`.
* Launch `!WinColl` (for example, by double left-clicking it).

WinColl should run on RISC OS 3.5 to 3.7, and could probably be made to run
on RISC OS 2 without difficulty.

You can edit the levels. Either use [Tiled](https://www.mapeditor.org/) and
convert them to WinColl’s plain text format with `tiled2level`, for which
the `pytmx` library is required; or use the BASIC program `LevelDes` that
lives in the `!WinColl` folder. (Shift+Left double-click to open the
folder).


## Copyright and Disclaimer

The package is distributed under the GNU Public License version 3, or, at
your option, any later version. See the file COPYING.

THIS PROGRAM IS PROVIDED AS IS, WITH NO WARRANTY. USE IS AT THE USER'S RISK.

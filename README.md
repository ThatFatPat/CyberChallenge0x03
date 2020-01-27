# CyberChallenge0x03

## Introduction and Setup
Another month, another cyber challenge. This one started out interesting enough but then became unexpectedly difficult all of a sudden. It was quite the ride! I'd like to take you through this journey with me.

First things first, let's read the instructions:

	The Goal:
	- You have been given a linux executable binary in unknown architecture.
	You are already familiar with x86 and hopefully with IDA.
	
	- First, try to find out what the architecture is ( hint: readelf) and then, understand the
	instruction set of the architecture (google is your friend).
	
	- Next, try to understand what the executable does.
	
	- Submit the correct input for that program.

OK, Simple enough. We get an executable in an unknown architecture, and our goal is to reverse it.

As suggested by the instructions, let's take a look at the output of `readelf`. Using the `-h` option to get information on the header, we get the following output:
```
ELF Header:
  Magic:   7f 45 4c 46 01 02 01 00 00 00 00 00 00 00 00 00 
  Class:                             ELF32
  Data:                              2's complement, big endian
  Version:                           1 (current)
  OS/ABI:                            UNIX - System V
  ABI Version:                       0
  Type:                              EXEC (Executable file)
  Machine:                           MIPS R3000
  Version:                           0x1
  Entry point address:               0x400600
  Start of program headers:          52 (bytes into file)
  Start of section headers:          6644 (bytes into file)
  Flags:                             0x70001007, noreorder, pic, cpic, o32, mips32r2
  Size of this header:               52 (bytes)
  Size of program headers:           32 (bytes)
  Number of program headers:         11
  Size of section headers:           40 (bytes)
  Number of section headers:         32
  Section header string table index: 31
```
Lots of nonsense, but there are a couple of important lines here. Namely, they are these:
```
Data:                              2's complement, big endian
Machine:                           MIPS R3000
```
And as we can see, the architecture for this program is MIPS. That was easy enough!
It's important to keep in mind the fact the the system is a 2's complement system in big endian. For those unfamiliar with the concepts, more info can be found here ([Endians](https://www.youtube.com/watch?v=NcaiHcBvDR4), [2's Complement](https://www.youtube.com/watch?v=lKTsv6iVxV4)).

Now that we've figured out the architecture, there are a couple of challenges ahead. Before we can start solving this binary, we need to find a way to run it so we can see what it does, and also to actually run it once we have solved it. To do that, we'll be using QEMU, a low-level emulation platform that can emulate pretty much any architecture on the market today (and also a lot of obsolete ones).

### Installing QEMU and other dependencies in order to execute MIPS code
In order to execute the binary we have to follow a couple of simple steps:
	1.Install QEMU
	2.Set up a chroot environment. *For a detailed explanation on `chroot` please refer to my solution for the previous challenge, found [here](https://github.com/ThatFatPat/CyberChallenge0x02)*
	3.Copy the necessary binaries into the chroot

The installation of QEMU itself is simple enough. Just use `apt` (or a package manager of your choice) to install the following packages: `qemu qemu-user-static`.
We'll need a few more dependencies for our purposes: `gdb-multiarch libc6-mips-cross`

That's step one done. With that out of the way, we need to create a chroot environment for our executables to live in. The reason for this is that the MIPS binary (and by extension it's emulator, QEMU), will try to link against our x86_64 binaries in order to execute the program. Because of the incompatability between the architectures, this will not work. One solution is to use the `-L` option in order to specify the path for the linker, but I've found this solution to be unreliable at best and non-functional most of the time. For this reason, using a chroot environment will assist us in preventing the architectural intermingling.

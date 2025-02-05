# CyberChallenge0x03

- [CyberChallenge0x03](#cyberchallenge0x03)
  * [Introduction and Setup](#introduction-and-setup)
  * [First Run](#first-run)
  * [Reversing The Binary](#reversing-the-binary)
    + [A Quick Overview of the MIPS Architecture](#a-quick-overview-of-the-mips-architecture)
      - [RISC vs. CISC](#risc-vs-cisc)
      - [General Purpose Registers](#general-purpose-registers)
      - [Instruction Set](#instruction-set)
    + [Examining the code](#examining-the-code)
    + [Main Body](#main-body)
      - [0x4007d8 - 0x4007ec](#0x4007d8---0x4007ec)
      - [String Table](#string-table)
      - [C Standard Library Function Address Reference Table](#c-standard-library-function-address-reference-table)
      - [0x4007f0 - 0x400810](#0x4007f0---0x400810)
      - [0x400814 - 0x400828](#0x400814---0x400828)
      - [0x400850 - 0x40086c](#0x400850---0x40086c)
      - [0x40089c - 0x4008b0](#0x40089c---0x4008b0)
      - [0x400870 - 0x4008b0](#0x400870---0x4008b0)
      - [0x4008b4 - 0x4008c0](#0x4008b4---0x4008c0)
      - [0x4008c4 - 0x4008e4](#0x4008c4---0x4008e4)
  * [Solution](#solution)
    + [Debugging with GDB](#debugging-with-gdb)
    + [2's complement](#2-s-complement)
    + [Sign extension](#sign-extension)
    + [What now then?](#what-now-then)
    + [Workaround 1: Patching the `lb` instruction](#workaround-1-patching-the-lb-instruction)
    + [Workaround 2: Patching the format string](#workaround-2-patching-the-format-string)
    + [Workaround 3: Patching the constant](#workaround-3-patching-the-constant)
    + [Workaround 4: Patching the branch](#workaround-4-patching-the-branch)
    + [Dynamic Memory Patching - Workaround 5](#dynamic-memory-patching---workaround-5)

## Introduction and Setup
Another month, another cyber challenge. This one started out interesting enough but then became unexpectedly difficult all of a sudden. It was quite the ride! I'd like to take you through this journey with me.

First things first, let's read the instructions:

	The Goal:
	- You have been given a linux executable binary in unknown architecture.
	You are already familiar with x86 and hopefully with IDA.
	
	- First, try to find out what the architecture is ( hint: readelf) and then, understand the
	instruction set of the architecture (google is your friend)
	
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

* Install QEMU
* Set up a chroot environment. 
* Copy the necessary binaries into the chroot
###### For a detailed explanation on `chroot` please refer to my solution for the previous challenge, found [here](https://github.com/ThatFatPat/CyberChallenge0x02#3rd-soultion-we-chrootin-boys)

The installation of QEMU itself is simple enough. Just use `apt` (or a package manager of your choice) to install the following packages: `qemu qemu-user-static`.
We'll need a few more dependencies for our purposes: `gdb-multiarch libc6-mips-cross`

That's step one done. With that out of the way, we need to create a chroot environment for our executables to live in. The reason for this is that the MIPS binary (and by extension it's emulator, QEMU), will try to link against our x86_64 binaries in order to execute the program. Because of the incompatability between the architectures, this will not work. One solution is to use the `-L` option in order to specify the path for the linker, but I've found this solution to be unreliable at best and non-functional most of the time. For this reason, using a chroot environment will assist us in preventing the architectural intermingling.

In order to actually set up the `chroot`:

* Start by creating a directory, let's call it `chroot_jail`.
* `sudo cp -r /usr/mips-linux-gnu/* chroot_jail`
* `sudo mkdir chroot_jail/bin`
* `sudo cp /usr/bin/qemu-mips-static chroot_jail/bin`
* `sudo cp challenge3 chroot_jail/bin`

What we've done is taken all of the compiled MIPS binaries we installed when installing `libc6-mips-cross` and moved them into our chroot directory, that way we have access to all the MIPS binaries our program might want to link against.
In addition, we've moved our `qemu-mips-static` (static means it can function without linking against our standard library) executable into our new `bin` directory, as well as the challenge, which is the executable we want to execute.

Now that we've created out `chroot` jail, we can go ahead and test it.

## First Run
We'll run our challenge program by `cd`-ing into our `chroot_jail` (Keep in mind this is important as the `chroot`-ed programs are unaware of the directory structure outside of our `chroot_jail` by design), and executing the following command:

```console
user@pc$ sudo chroot . qemu-mips-static bin/challenge3
```
Basically, we are passing the `challenge3` executable to `qemu-mips-static` so it can run it.

The output we get is simple enough:
```
Please, enter a password : 
```
And should we try to enter one:
```
Please, enter a password : AAAAAAAAAAAAAAAAAAA

wrong password!
```

To be expected. 

But we can fix that, now can't we?
And so, our journey begins.

## Reversing The Binary
As per the recommendation of the challenge creator, we'll refrain from using decompilers in reversing this binary. If so, we can only use our brains for this exercise. Before opening our trusted Ghidra to assist us with deciphering this binary, there are a couple of things we can do a little less "robustly".

In order to take a look at the disassembly, we can use `objdump` - A tool for "dumping" the data and assembly code of binaries. Let's try to run it on our binary:
```console
user@pc$ objdump -d bin/challenge3

bin/challenge3:     file format elf32-big

objdump: can't disassemble for architecture UNKNOWN!
```
Oh no! `objdump` is telling us that it cannot disassemble our binary as it's architecture is unknown. What's happening here in fact is that our version of `objdump` is only built to handle x86(\_64) binaries, and as we've already learned, our binary is of the MIPS architechture.

There is more than one solution to the following issue, but the one we'll be discussing is the simplest one, offered by our already-installed dependencies. (Although I encourage investigative readers to look into `llvm-objdump`)

By installing `libc6-mips-cross`, we installed some libraries and binaries built to handle the MIPS arch. Among them is `mips-linux-gnu-objdump`, which we can use to `objdump` our binary.

Running the following command:
```console
user@pc$ mips-linux-gnu-objdump -d bin/challenge3
```
We get the following output:
```asm

bin/challenge3:     file format elf32-tradbigmips


Disassembly of section .init:

	00400584 <_init>:

Disassembly of section .text:

	00400600 <__start>:

	00400650 <hlt>:

	00400660 <deregister_tm_clones>:

	00400698 <register_tm_clones>:

	004006e4 <__do_global_dtors_aux>:

	00400794 <frame_dummy>:

	004007a0 <main>:
	  4007a0:	27bdffc8 	addiu	sp,sp,-56
	  4007a4:	afbf0034 	sw	ra,52(sp)
	  4007a8:	afbe0030 	sw	s8,48(sp)
	  4007ac:	03a0f025 	move	s8,sp
	  4007b0:	3c1c0042 	lui	gp,0x42
	  4007b4:	279c9010 	addiu	gp,gp,-28656
	  4007b8:	afbc0010 	sw	gp,16(sp)
	  4007bc:	afc00024 	sw	zero,36(s8)
	  4007c0:	afc00028 	sw	zero,40(s8)
	  4007c4:	a7c0002c 	sh	zero,44(s8)
	  4007c8:	24020001 	li	v0,1
	  4007cc:	afc20020 	sw	v0,32(s8)
	  4007d0:	afc00018 	sw	zero,24(s8)
	  4007d4:	afc0001c 	sw	zero,28(s8)
	  4007d8:	3c020040 	lui	v0,0x40
	  4007dc:	24440af0 	addiu	a0,v0,2800
	  4007e0:	8f828054 	lw	v0,-32684(gp)
	  4007e4:	0040c825 	move	t9,v0
	  4007e8:	0320f809 	jalr	t9
	  4007ec:	00000000 	nop
	  4007f0:	8fdc0010 	lw	gp,16(s8)
	  4007f4:	27c20024 	addiu	v0,s8,36
	  4007f8:	00402825 	move	a1,v0
	  4007fc:	3c020040 	lui	v0,0x40
	  400800:	24440b0c 	addiu	a0,v0,2828
	  400804:	8f828040 	lw	v0,-32704(gp)
	  400808:	0040c825 	move	t9,v0
	  40080c:	0320f809 	jalr	t9
	  400810:	00000000 	nop
	  400814:	8fdc0010 	lw	gp,16(s8)
	  400818:	afc20020 	sw	v0,32(s8)
	  40081c:	8fc30020 	lw	v1,32(s8)
	  400820:	24020001 	li	v0,1
	  400824:	1062000a 	beq	v1,v0,400850 <main+0xb0>
	  400828:	00000000 	nop
	  40082c:	3c020040 	lui	v0,0x40
	  400830:	24440b14 	addiu	a0,v0,2836
	  400834:	8f828050 	lw	v0,-32688(gp)
	  400838:	0040c825 	move	t9,v0
	  40083c:	0320f809 	jalr	t9
	  400840:	00000000 	nop
	  400844:	8fdc0010 	lw	gp,16(s8)
	  400848:	1000002e 	b	400904 <main+0x164>
	  40084c:	00000000 	nop
	  400850:	2404000a 	li	a0,10
	  400854:	8f828044 	lw	v0,-32700(gp)
	  400858:	0040c825 	move	t9,v0
	  40085c:	0320f809 	jalr	t9
	  400860:	00000000 	nop
	  400864:	8fdc0010 	lw	gp,16(s8)
	  400868:	1000000c 	b	40089c <main+0xfc>
	  40086c:	00000000 	nop
	  400870:	8fc20018 	lw	v0,24(s8)
	  400874:	27c30018 	addiu	v1,s8,24
	  400878:	00621021 	addu	v0,v1,v0
	  40087c:	8042000c 	lb	v0,12(v0)
	  400880:	00401825 	move	v1,v0
	  400884:	8fc2001c 	lw	v0,28(s8)
	  400888:	00431021 	addu	v0,v0,v1
	  40088c:	afc2001c 	sw	v0,28(s8)
	  400890:	8fc20018 	lw	v0,24(s8)
	  400894:	24420001 	addiu	v0,v0,1
	  400898:	afc20018 	sw	v0,24(s8)
	  40089c:	8fc20018 	lw	v0,24(s8)
	  4008a0:	27c30018 	addiu	v1,s8,24
	  4008a4:	00621021 	addu	v0,v1,v0
	  4008a8:	8042000c 	lb	v0,12(v0)
	  4008ac:	1440fff0 	bnez	v0,400870 <main+0xd0>
	  4008b0:	00000000 	nop
	  4008b4:	8fc3001c 	lw	v1,28(s8)
	  4008b8:	24020539 	li	v0,1337
	  4008bc:	1462000a 	bne	v1,v0,4008e8 <main+0x148>
	  4008c0:	00000000 	nop
	  4008c4:	3c020040 	lui	v0,0x40
	  4008c8:	24440b2c 	addiu	a0,v0,2860
	  4008cc:	8f828050 	lw	v0,-32688(gp)
	  4008d0:	0040c825 	move	t9,v0
	  4008d4:	0320f809 	jalr	t9
	  4008d8:	00000000 	nop
	  4008dc:	8fdc0010 	lw	gp,16(s8)
	  4008e0:	10000008 	b	400904 <main+0x164>
	  4008e4:	00000000 	nop
	  4008e8:	3c020040 	lui	v0,0x40
	  4008ec:	24440b40 	addiu	a0,v0,2880
	  4008f0:	8f828050 	lw	v0,-32688(gp)
	  4008f4:	0040c825 	move	t9,v0
	  4008f8:	0320f809 	jalr	t9
	  4008fc:	00000000 	nop
	  400900:	8fdc0010 	lw	gp,16(s8)
	  400904:	8fc20020 	lw	v0,32(s8)
	  400908:	03c0e825 	move	sp,s8
	  40090c:	8fbf0034 	lw	ra,52(sp)
	  400910:	8fbe0030 	lw	s8,48(sp)
	  400914:	27bd0038 	addiu	sp,sp,56
	  400918:	03e00008 	jr	ra
	  40091c:	00000000 	nop

	00400920 <__libc_csu_init>:

	004009c4 <__libc_csu_fini>:

	004009d0 <__do_global_ctors_aux>:

Disassembly of section .MIPS.stubs:

	00400a30 <_MIPS_STUBS_>:

Disassembly of section .fini:

	00400a90 <_fini>:
```

For simplicity's sake, I've removed all the boilerplate code from the disassembly output. This code is very similar between different binaries and has almost nothing to do with the actual program code.

Looking at the output of `objdump`, we already have one important piece of information, even before diving deep into the code: **The binary only contains a main function** (Unless other functions were fuzzed somehow, but this is not probable in a simple challenge such as this).

Equipped with this information, we can start reversing our binary.

### A Quick Overview of the MIPS Architecture
**Before we take a look at the MIPS Architecture, a quick disclaimer**: I'm no authority on the MIPS architecture, nor am I able to share all of my knowledge on the topic in such short form. Therfore, this overview has gaps in it, stemming from lack of time and ability to cram massive amounts of material into a challenge guide. If you'd like to deep-dive into the MIPS architecture, I encourage you to take a look at [this](https://courses.cs.washington.edu/courses/cse378/11wi/lectures.html) lovely course offered by UW, or alternativley, take the course Computer Structures at TAU, which covers all of the topics discussed here at length.

With that out of the way, let's take a look at the MIPS ISA (Instruction Set Architecture).

#### RISC vs. CISC
The MIPS ISA is based on the RISC philosophy, standing for 'Reduced Instruction Set Computer'. This is opposed to the CISC approach (Complex Instruciton Set Computer), supported by the likes of Intel's x86. The debate around the two philosophies arose around the early 1980's. Today, only Intel's x86 still supports the CISC philosophy, while most other architectures, such as ARM and MIPS, use the RISC approach when implementing their ISAs.

The main differences between RISC and CISC can be summarized as follows:

| RISC | CISC |
|------|------|
| Set length instructions | Variable length instructions |
| Stronger reliance on software | More reliance on hardware-implemented routines |
| More seperation between memory and registers, LOAD and STORE are seperate instructions | Can perform operations directly* on memory |

###### * Please read the supplied article 
###### More information on the topic can be found [here](https://cs.stanford.edu/people/eroberts/courses/soco/projects/risc/risccisc/)

#### General Purpose Registers
The MIPS ISA specifies 32 general purpose registers. Use the following table as a reference:

| Number | Name | Purpose |
|--------|------|---------|
| $0 | $0 | Always 0 |
| $1 | $at | The Assembler Temporary used by the assembler in expanding pseudo-ops. |
| $2-$3 | $v0-$v1 | These registers contain the Returned Value of a subroutine; if the value is 1 word only $v0 is significant. |
| $4-$7 | $a0-$a3 | The Argument registers, these registers contain the first 4 argument values for a subroutine call. |
| $8-$15, $24,$25 | $t0-$t9 | The Temporary Registers. |
| $16-$23 | $s0-$s7 | The Saved Registers. |
| $26-$27 | $k0-$k1 | The Kernel Reserved registers. DO NOT USE. |
| $28 | $gp | The Globals Pointer used for addressing static global variables. |
| $29 | $sp | The Stack Pointer. |
| $30 | $fp (or $s8) | The Frame Pointer. [What are frame pointers?](https://softwareengineering.stackexchange.com/a/194341) |
| $31 | $ra | The Return Address in a subroutine call. |

###### Adapted from UW CSE410 ([Source](https://courses.cs.washington.edu/courses/cse410/09sp/examples/MIPSCallingConventionsSummary.pdf))

#### Instruction Set
In accordance with the RISC philosophy, MIPS instructions are fixed size. Each instruction is exactly one word, where a word is 32 bits.

Instructions are divided into three types: R, I and J. Every instruction starts with a 6-bit opcode. (For R-type instructions this is always 0). In addition to the opcode, R-type instructions specify three registers, a shift amount field, and a function field; I-type instructions specify two registers and a 16-bit immediate value; J-type instructions follow the opcode with a 26-bit jump target.

The following are the three formats used for the core instruction set:

<table>

<tbody><tr>
<th>Type</th>
<th colspan="6">-31- &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; format (bits) &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; -0-
</th></tr>
<tr align="center">
<td><b>R</b></td>
<td>000000</td>
<td>rs (5)</td>
<td>rt (5)</td>
<td>rd (5)</td>
<td>shamt (5)</td>
<td>funct (6)
</td></tr>
<tr align="center">
<td><b>I</b></td>
<td>opcode (6)</td>
<td>rs (5)</td>
<td>rt (5)</td>
<td colspan="3">immediate (16)
</td></tr>
<tr align="center">
<td><b>J</b></td>
<td>opcode (6)</td>
<td colspan="5">address (26)
</td></tr></tbody></table>

###### [Source](https://en.wikipedia.org/wiki/MIPS_architecture)

If you do not know the MIPS architecture, I recommend reading/executing this guide with an instruction reference on another tab, so that you can easily follow along.

The MIPS ISA can be found [here](http://www.mrc.uidaho.edu/mrc/people/jff/digital/MIPSir.html) (Missing some instructions, the rest can be found online if you just google them).

### Examining the code
Equipped with a basic understanding of the MIPS architecture, we can start to look through this binary and understand it's actions.

Let's take another look at main, this time just adding newlines between branches and branch targets:
```asm
	004007a0 <main>:
	  4007a0:	27bdffc8 	addiu	sp,sp,-56
	  4007a4:	afbf0034 	sw	ra,52(sp)
	  4007a8:	afbe0030 	sw	s8,48(sp)
	  4007ac:	03a0f025 	move	s8,sp
	  4007b0:	3c1c0042 	lui	gp,0x42
	  4007b4:	279c9010 	addiu	gp,gp,-28656
	  4007b8:	afbc0010 	sw	gp,16(sp)
	  4007bc:	afc00024 	sw	zero,36(s8)
	  4007c0:	afc00028 	sw	zero,40(s8)
	  4007c4:	a7c0002c 	sh	zero,44(s8)
	  4007c8:	24020001 	li	v0,1
	  4007cc:	afc20020 	sw	v0,32(s8)
	  4007d0:	afc00018 	sw	zero,24(s8)
	  4007d4:	afc0001c 	sw	zero,28(s8)
	  4007d8:	3c020040 	lui	v0,0x40
	  4007dc:	24440af0 	addiu	a0,v0,2800
	  4007e0:	8f828054 	lw	v0,-32684(gp)
	  4007e4:	0040c825 	move	t9,v0
	  4007e8:	0320f809 	jalr	t9
	  4007ec:	00000000 	nop
	  4007f0:	8fdc0010 	lw	gp,16(s8)
	  4007f4:	27c20024 	addiu	v0,s8,36
	  4007f8:	00402825 	move	a1,v0
	  4007fc:	3c020040 	lui	v0,0x40
	  400800:	24440b0c 	addiu	a0,v0,2828
	  400804:	8f828040 	lw	v0,-32704(gp)
	  400808:	0040c825 	move	t9,v0
	  40080c:	0320f809 	jalr	t9
	  400810:	00000000 	nop
	  400814:	8fdc0010 	lw	gp,16(s8)
	  400818:	afc20020 	sw	v0,32(s8)
	  40081c:	8fc30020 	lw	v1,32(s8)
	  400820:	24020001 	li	v0,1
	  400824:	1062000a 	beq	v1,v0,400850 <main+0xb0>
	  400828:	00000000 	nop
	  
	40082c:		3c020040 	lui	v0,0x40
	  400830:	24440b14 	addiu	a0,v0,2836
	  400834:	8f828050 	lw	v0,-32688(gp)
	  400838:	0040c825 	move	t9,v0
	  40083c:	0320f809 	jalr	t9
	  400840:	00000000 	nop
	  400844:	8fdc0010 	lw	gp,16(s8)
	  400848:	1000002e 	b	400904 <main+0x164>
	  40084c:	00000000 	nop
	  
	400850:		2404000a 	li	a0,10
	  400854:	8f828044 	lw	v0,-32700(gp)
	  400858:	0040c825 	move	t9,v0
	  40085c:	0320f809 	jalr	t9
	  400860:	00000000 	nop
	  400864:	8fdc0010 	lw	gp,16(s8)
	  400868:	1000000c 	b	40089c <main+0xfc>
	  40086c:	00000000 	nop
	  
	400870:		8fc20018 	lw	v0,24(s8)
	  400874:	27c30018 	addiu	v1,s8,24
	  400878:	00621021 	addu	v0,v1,v0
	  40087c:	8042000c 	lb	v0,12(v0)
	  400880:	00401825 	move	v1,v0
	  400884:	8fc2001c 	lw	v0,28(s8)
	  400888:	00431021 	addu	v0,v0,v1
	  40088c:	afc2001c 	sw	v0,28(s8)
	  400890:	8fc20018 	lw	v0,24(s8)
	  400894:	24420001 	addiu	v0,v0,1
	  400898:	afc20018 	sw	v0,24(s8)
	  
	40089c:		8fc20018 	lw	v0,24(s8)
	  4008a0:	27c30018 	addiu	v1,s8,24
	  4008a4:	00621021 	addu	v0,v1,v0
	  4008a8:	8042000c 	lb	v0,12(v0)
	  4008ac:	1440fff0 	bnez	v0,400870 <main+0xd0>
	  4008b0:	00000000 	nop
	  
	4008b4:		8fc3001c 	lw	v1,28(s8)
	  4008b8:	24020539 	li	v0,1337
	  4008bc:	1462000a 	bne	v1,v0,4008e8 <main+0x148>
	  4008c0:	00000000 	nop
	  
	4008c4:		3c020040 	lui	v0,0x40
	  4008c8:	24440b2c 	addiu	a0,v0,2860
	  4008cc:	8f828050 	lw	v0,-32688(gp)
	  4008d0:	0040c825 	move	t9,v0
	  4008d4:	0320f809 	jalr	t9
	  4008d8:	00000000 	nop
	  4008dc:	8fdc0010 	lw	gp,16(s8)
	  4008e0:	10000008 	b	400904 <main+0x164>
	  4008e4:	00000000 	nop
	  
	4008e8:		3c020040 	lui	v0,0x40
	  4008ec:	24440b40 	addiu	a0,v0,2880
	  4008f0:	8f828050 	lw	v0,-32688(gp)
	  4008f4:	0040c825 	move	t9,v0
	  4008f8:	0320f809 	jalr	t9
	  4008fc:	00000000 	nop
	  400900:	8fdc0010 	lw	gp,16(s8)
	  
	400904:		8fc20020 	lw	v0,32(s8)
	  400908:	03c0e825 	move	sp,s8
	  40090c:	8fbf0034 	lw	ra,52(sp)
	  400910:	8fbe0030 	lw	s8,48(sp)
	  400914:	27bd0038 	addiu	sp,sp,56
	  400918:	03e00008 	jr	ra
	  40091c:	00000000 	nop
```
By doing this, we can get a sense for the flow of the program, and start to construct a flow graph in our mind.

*It is recommended to grab a pen and some paper, and roughly sketch the graph for the program in order to get a better sense of what's happening. I will not be drawing control graphs here, because of the limitations of the medium.*

The next passthrough we'll do is just seperating the [prolouge](https://en.wikipedia.org/wiki/Function_prologue), and other subroutine calls so that we can spot them easily.
```asm
	004007a0 <main>:
	  4007a0:	27bdffc8 	addiu	sp,sp,-56
	  4007a4:	afbf0034 	sw	ra,52(sp)
	  4007a8:	afbe0030 	sw	s8,48(sp)
	  4007ac:	03a0f025 	move	s8,sp
	  4007b0:	3c1c0042 	lui	gp,0x42
	  4007b4:	279c9010 	addiu	gp,gp,-28656
	  4007b8:	afbc0010 	sw	gp,16(sp)
	  4007bc:	afc00024 	sw	zero,36(s8)
	  4007c0:	afc00028 	sw	zero,40(s8)
	  4007c4:	a7c0002c 	sh	zero,44(s8)
	  4007c8:	24020001 	li	v0,1
	  4007cc:	afc20020 	sw	v0,32(s8)
	  4007d0:	afc00018 	sw	zero,24(s8)
	  4007d4:	afc0001c 	sw	zero,28(s8)
	  
	  4007d8:	3c020040 	lui	v0,0x40
	  4007dc:	24440af0 	addiu	a0,v0,2800
	  4007e0:	8f828054 	lw	v0,-32684(gp)
	  4007e4:	0040c825 	move	t9,v0
	  4007e8:	0320f809 	jalr	t9
	  4007ec:	00000000 	nop
	  
	  4007f0:	8fdc0010 	lw	gp,16(s8)
	  4007f4:	27c20024 	addiu	v0,s8,36
	  4007f8:	00402825 	move	a1,v0
	  4007fc:	3c020040 	lui	v0,0x40
	  400800:	24440b0c 	addiu	a0,v0,2828
	  400804:	8f828040 	lw	v0,-32704(gp)
	  400808:	0040c825 	move	t9,v0
	  40080c:	0320f809 	jalr	t9
	  400810:	00000000 	nop
	  
	  400814:	8fdc0010 	lw	gp,16(s8)
	  400818:	afc20020 	sw	v0,32(s8)
	  40081c:	8fc30020 	lw	v1,32(s8)
	  400820:	24020001 	li	v0,1
	  400824:	1062000a 	beq	v1,v0,400850 <main+0xb0>
	  400828:	00000000 	nop
	  
	  
	40082c:		3c020040 	lui	v0,0x40
	  400830:	24440b14 	addiu	a0,v0,2836
	  400834:	8f828050 	lw	v0,-32688(gp)
	  400838:	0040c825 	move	t9,v0
	  40083c:	0320f809 	jalr	t9
	  400840:	00000000 	nop
	  
	  400844:	8fdc0010 	lw	gp,16(s8)
	  400848:	1000002e 	b	400904 <main+0x164>
	  40084c:	00000000 	nop
	  
	  
	400850:		2404000a 	li	a0,10
	  400854:	8f828044 	lw	v0,-32700(gp)
	  400858:	0040c825 	move	t9,v0
	  40085c:	0320f809 	jalr	t9
	  400860:	00000000 	nop
	  
	  400864:	8fdc0010 	lw	gp,16(s8)
	  400868:	1000000c 	b	40089c <main+0xfc>
	  40086c:	00000000 	nop
	  
	  
	400870:		8fc20018 	lw	v0,24(s8)
	  400874:	27c30018 	addiu	v1,s8,24
	  400878:	00621021 	addu	v0,v1,v0
	  40087c:	8042000c 	lb	v0,12(v0)
	  400880:	00401825 	move	v1,v0
	  400884:	8fc2001c 	lw	v0,28(s8)
	  400888:	00431021 	addu	v0,v0,v1
	  40088c:	afc2001c 	sw	v0,28(s8)
	  400890:	8fc20018 	lw	v0,24(s8)
	  400894:	24420001 	addiu	v0,v0,1
	  400898:	afc20018 	sw	v0,24(s8)
	  
	  
	40089c:		8fc20018 	lw	v0,24(s8)
	  4008a0:	27c30018 	addiu	v1,s8,24
	  4008a4:	00621021 	addu	v0,v1,v0
	  4008a8:	8042000c 	lb	v0,12(v0)
	  4008ac:	1440fff0 	bnez	v0,400870 <main+0xd0>
	  4008b0:	00000000 	nop
	  
	  
	4008b4:		8fc3001c 	lw	v1,28(s8)
	  4008b8:	24020539 	li	v0,1337
	  4008bc:	1462000a 	bne	v1,v0,4008e8 <main+0x148>
	  4008c0:	00000000 	nop
	  
	  
	4008c4:		3c020040 	lui	v0,0x40
	  4008c8:	24440b2c 	addiu	a0,v0,2860
	  4008cc:	8f828050 	lw	v0,-32688(gp)
	  4008d0:	0040c825 	move	t9,v0
	  4008d4:	0320f809 	jalr	t9
	  4008d8:	00000000 	nop
	  
	  4008dc:	8fdc0010 	lw	gp,16(s8)
	  4008e0:	10000008 	b	400904 <main+0x164>
	  4008e4:	00000000 	nop
	  
	  
	4008e8:		3c020040 	lui	v0,0x40
	  4008ec:	24440b40 	addiu	a0,v0,2880
	  4008f0:	8f828050 	lw	v0,-32688(gp)
	  4008f4:	0040c825 	move	t9,v0
	  4008f8:	0320f809 	jalr	t9
	  4008fc:	00000000 	nop
	  
	  400900:	8fdc0010 	lw	gp,16(s8)
	  
	400904:		8fc20020 	lw	v0,32(s8)
	  400908:	03c0e825 	move	sp,s8
	  40090c:	8fbf0034 	lw	ra,52(sp)
	  400910:	8fbe0030 	lw	s8,48(sp)
	  400914:	27bd0038 	addiu	sp,sp,56
	  400918:	03e00008 	jr	ra
	  40091c:	00000000 	nop

```
There we go. Before even trying to understand what the code does, we can look structure it in such a way that helps us deal with it more easily.

Now that we're done with the first passthrough, let's go over the function part-by-part, analyzing as we go.

#### Prolouge
The prolouge of the function sets up the stack and zeros out variables. Let's take a look:
```asm
  4007a0:	addiu	sp,sp,-56
  4007a4:	sw	ra,52(sp)
  4007a8:	sw	s8,48(sp)
  4007ac:	move	s8,sp
  
  4007b0:	lui	gp,0x42
  4007b4:	addiu	gp,gp,-28656
  4007b8:	sw	gp,16(sp)
  
  4007bc:	sw	zero,36(s8)
  4007c0:	sw	zero,40(s8)
  4007c4:	sh	zero,44(s8)
  4007c8:	li	v0,1
  4007cc:	sw	v0,32(s8)
  4007d0:	sw	zero,24(s8)
  4007d4:	sw	zero,28(s8)
```
The prolouge can be divided into 3 parts:
1. Allocating space on the stack (sp = sp-56) and saving the return address and the frame pointer.
2. Setting up the global pointer, which we'll use to read strings from .rodata or call C Standard Library functions from the symbol table.
3. Zeroing out some variables on the stack, storing 0x1 at $sp+32 (s8 == sp).

Let's take a close look at #2:
```asm
  4007b0:	lui	gp,0x42
  4007b4:	addiu	gp,gp,-28656
 ```
This code can be translated to pseudo-python as follows:
```python
gp = (0x42 << 16) - 28656 # 4296720 (0x419010)
stack[16] = gp # This is inaccurate, but it's difficult to represent a stack in python.
```
Well, if `$gp` just ends up with a value of `0x419010`, why not just use a simple `addiu` like so:
```asm
	addiu 	gp, 0x419010
```
There's a reason for that, and it's stemming from necessity. If you think back to the MIPS overview, you'll remember that in order to use immediates we'll have to rely on an I-type instruction. I-type instructions, by design, can only contain 16-bit offsets. Since the value of 0x419010 exceeds 16-bits, we'll have to find some other way to load the high 16-bits into `$gp`.

To do that, we'll use a `lui` instruction, which stores the immediate it gets as the **high** 16 bits of a register. And so, we can manipulate the original offset (0x419010) such that it is calculated using two instructions. This method is used extensivly throughout the code, as it is our only way of addressing the high regions of the memory space, where all our globals are loaded.

Now that we've analyzed the prolouge, let's move on.

### Main Body
In order to see the bigger picture, we'll need to dive into pieces of code in order to decipher them. We've done all that we possibly can in order to simplify the process for us, but now we have no choice but to take our divided function and analyze each part seperatly so we can see how it fits into the bigger picture.

#### 0x4007d8 - 0x4007ec
```asm
	  4007d8:	lui	v0,0x40
	  4007dc:	addiu	a0,v0,2800
	  4007e0:	lw	v0,-32684(gp)
	  4007e4:	move	t9,v0
	  4007e8:	jalr	t9
	  4007ec:	nop
```
As we've already established, we'll use the `lui` instruction and the global pointer `gp` in order to access C Standard Library functions and globals such as strings stored in the .rodata section.

Here we can see both of these use cases in action.
The `jalr` instruction is used in order to execute a subroutine call, that much we know from our MIPS overview. We also know that `$a0 - $a4` are arguments for the subroutine call. If so, we can already tell that this piece of code executes the following (simplified) pseudo code:
```c
t9 = **SOME_CALCULATED_ADDRESS**;
a0 = **SOME_CALCULATED_ADDRESS**;
t9(a0);
```
If so, we should only calculate the addresses of the function and it's argument in order to solve this piece of code.
```python
v0 = 0x40 << 16
a0 = v0 + 2800
v0 = *(gp - 32684)
t9 = v0
```
From this, we already know that:

* `$a0 = 0x400af0`
* `t9 = *(gp - 32684)`

We can use our previously calculated value for `$gp` (0x419010) in order to calculate `$t9`'s address.
```python
t9 = 0x411064
```
So all this gives us to addresses to investigate:

* `$a0 = 0x400af0`
* `t9 = *(0x411064)`

In order to investigate them, it would be helpful to know where they are located, section-wise.
We can use `readelf` with the `-S` (capital) for Section Headers to get the following output:
```console
user@pc$ readelf -S bin/challenge3
There are 32 section headers, starting at offset 0x19f4:

Section Headers:
  [Nr] Name              Type            Addr     Off    Size   ES Flg Lk Inf Al
  [ 0]                   NULL            00000000 000000 000000 00      0   0  0
  [ 1] .interp           PROGBITS        00400194 000194 00000d 00   A  0   0  1
  [ 2] .note.ABI-tag     NOTE            004001a4 0001a4 000020 00   A  0   0  4
  [ 3] .MIPS.abiflags    MIPS_ABIFLAGS   004001c8 0001c8 000018 18   A  0   0  8
  [ 4] .reginfo          MIPS_REGINFO    004001e0 0001e0 000018 18   A  0   0  4
  [ 5] .note.gnu.build-i NOTE            004001f8 0001f8 000024 00   A  0   0  4
  [ 6] .dynamic          DYNAMIC         0040021c 00021c 0000e0 08   A  9   0  4
  [ 7] .hash             HASH            004002fc 0002fc 000054 04   A  8   0  4
  [ 8] .dynsym           DYNSYM          00400350 000350 000100 10   A  9   1  4
  [ 9] .dynstr           STRTAB          00400450 000450 0000e3 00   A  0   0  1
  [10] .gnu.version      VERSYM          00400534 000534 000020 02   A  8   0  2
  [11] .gnu.version_r    VERNEED         00400554 000554 000030 00   A  9   1  4
  [12] .init             PROGBITS        00400584 000584 00007c 00  AX  0   0  4
  [13] .text             PROGBITS        00400600 000600 000430 00  AX  0   0 16
  [14] .MIPS.stubs       PROGBITS        00400a30 000a30 000060 00  AX  0   0  4
  [15] .fini             PROGBITS        00400a90 000a90 000044 00  AX  0   0  4
  [16] .rodata           PROGBITS        00400ae0 000ae0 000080 00   A  0   0 16
  [17] .eh_frame         PROGBITS        00400b60 000b60 000004 00   A  0   0  4
  [18] .ctors            PROGBITS        00410ff0 000ff0 000008 00  WA  0   0  4
  [19] .dtors            PROGBITS        00410ff8 000ff8 000008 00  WA  0   0  4
  [20] .data             PROGBITS        00411000 001000 000010 00  WA  0   0 16
  [21] .rld_map          PROGBITS        00411010 001010 000004 00  WA  0   0  4
  [22] .got              PROGBITS        00411020 001020 00004c 04 WAp  0   0 16
  [23] .sdata            PROGBITS        0041106c 00106c 000004 00 WAp  0   0  4
  [24] .bss              NOBITS          00411070 001070 000010 00  WA  0   0 16
  [25] .comment          PROGBITS        00000000 001070 00002b 01  MS  0   0  1
  [26] .pdr              PROGBITS        00000000 00109c 000060 00      0   0  4
  [27] .gnu.attributes   GNU_ATTRIBUTES  00000000 0010fc 000010 00      0   0  1
  [28] .mdebug.abi32     PROGBITS        00000000 00110c 000000 00      0   0  1
  [29] .symtab           SYMTAB          00000000 00110c 000500 10     30  51  4
  [30] .strtab           STRTAB          00000000 00160c 0002c5 00      0   0  1
  [31] .shstrtab         STRTAB          00000000 0018d1 000121 00      0   0  1
Key to Flags:
  W (write), A (alloc), X (execute), M (merge), S (strings), I (info),
  L (link order), O (extra OS processing required), G (group), T (TLS),
  C (compressed), x (unknown), o (OS specific), E (exclude),
  p (processor specific)
```
Ugh. Lots of text. By carefully scanning the table, we can find the two relevant sections:

* 0x0400af0: `[16] .rodata           PROGBITS        00400ae0 000ae0 000080 00   A  0   0 16`
* 0x0411064: `[22] .got              PROGBITS        00411020 001020 00004c 04 WAp  0   0 16`

This makes a lot of sense. We are calling a function using the GOT ([Global Offset Table](https://systemoverlord.com/2017/03/19/got-and-plt-for-pwning.html)), and passing it some address in `.rodata` (A section for read-only data and strings).

Let's decipher these one by one. First, the address in `.rodata`:

In order to examine this section, we can use `readelf`'s `-p` option in order to string-dump a section.
```console
user@pc$ readelf -p .rodata bin/challenge3

String dump of section '.rodata':
  [    10]  Please, enter a password : 
  [    2c]  %10s
  [    34]  no password entered! 
  [    4c]  correct password! 
  [    60]  wrong password! 
```
Very nice! These are all our strings, complete with offsets from the base address of the `.rodata` section.
Let's apply the offset of .rodata and store them in a table, so we can refer back to it later:

#### String Table

| Address | Length | Data |
|---------|--------|------|
| 0x0400af0 | 0x1c 	| "Please, enter a password : \x00" |
| 0x0400b0c | 0x5 	| "%10s\x00" |
| 0x0400b14 | 0x16 	| "no password entered! \x00" |
| 0x0400b2c | 0x13 	| "correct password! \x00" |
| 0x0400b40 | 0x11 	| "wrong password! \x00" |

###### Note: \x00 is of course the null-terminator, and is calculated into length.

Looking at the table, we can easily recognize the address as the "Please, enter a password : " string that greets us upon running the program. From this, it's also easy to make an educated guess about the function being passed the string, seeing as it prints it to the console. We now know it's probably either `printf` or `puts`, but we still can't be sure.

Let's now take a look at the second address - `0x411064`:

We know this address resides inside the Global Offset Table, which is a table storing address for position-independent code. For a detailed explanation on this section, please refer to [this](https://systemoverlord.com/2017/03/19/got-and-plt-for-pwning.html) lovely blog post.

Equipped with knowledge about the GOT, we can try to use `readelf` in order to find some way to parse the GOT. By using the `-A` option for architecture-specific information, we can extract the following output:
```console
user@pc$ readelf -A bin/challenge3
Attribute Section: gnu
File Attributes
  Tag_GNU_MIPS_ABI_FP: Hard float (32-bit CPU, Any FPU)

MIPS ABI Flags Version: 0

ISA: MIPS32r2
GPR size: 32
CPR1 size: 32
CPR2 size: 0
FP ABI: Hard float (32-bit CPU, Any FPU)
ISA Extension: None
ASEs:
	None
FLAGS 1: 00000000
FLAGS 2: 00000000

Primary GOT:
 Canonical gp value: 00419010

 Reserved entries:
   Address     Access  Initial Purpose
  00411020 -32752(gp) 00000000 Lazy resolver
  00411024 -32748(gp) 80000000 Module pointer (GNU extension)

 Local entries:
   Address     Access  Initial
  00411028 -32744(gp) 004007a0
  0041102c -32740(gp) 00400920
  00411030 -32736(gp) 004009c4
  00411034 -32732(gp) 00400000
  00411038 -32728(gp) 00400584
  0041103c -32724(gp) 00410ff0
  00411040 -32720(gp) 00000000
  00411044 -32716(gp) 00000000
  00411048 -32712(gp) 00000000

 Global entries:
   Address     Access  Initial Sym.Val. Type    Ndx Name
  0041104c -32708(gp) 00000000 00000000 NOTYPE  UND _ITM_registerTMCloneTable
  00411050 -32704(gp) 00400a70 00400a70 FUNC    UND __isoc99_scanf
  00411054 -32700(gp) 00400a60 00400a60 FUNC    UND putchar
  00411058 -32696(gp) 00400a50 00400a50 FUNC    UND __libc_start_main
  0041105c -32692(gp) 00000000 00000000 FUNC    UND __gmon_start__
  00411060 -32688(gp) 00400a40 00400a40 FUNC    UND puts
  00411064 -32684(gp) 00400a30 00400a30 FUNC    UND printf
  00411068 -32680(gp) 00000000 00000000 NOTYPE  UND _ITM_deregisterTMCloneTable
```
This is a lot of information, but right at the end we can find the table we're looking for:
```console
 Global entries:
   Address     Access  Initial Sym.Val. Type    Ndx Name
  0041104c -32708(gp) 00000000 00000000 NOTYPE  UND _ITM_registerTMCloneTable
  00411050 -32704(gp) 00400a70 00400a70 FUNC    UND __isoc99_scanf
  00411054 -32700(gp) 00400a60 00400a60 FUNC    UND putchar
  00411058 -32696(gp) 00400a50 00400a50 FUNC    UND __libc_start_main
  0041105c -32692(gp) 00000000 00000000 FUNC    UND __gmon_start__
  00411060 -32688(gp) 00400a40 00400a40 FUNC    UND puts
  00411064 -32684(gp) 00400a30 00400a30 FUNC    UND printf
  00411068 -32680(gp) 00000000 00000000 NOTYPE  UND _ITM_deregisterTMCloneTable
 ```
 Using this information, we can construct a reference table for us to use later. We won't insert all of the boilerplate functions as to not bloat the table.
 
 #### C Standard Library Function Address Reference Table
 | Address | Access | Name |
 |---------|--------|------|
 | 0x00411050 | -32704(gp) | \_\_isoc99_scanf |
 | 0x00411054 | -32700(gp) | putchar |
 | 0x00411060 | -32688(gp) | puts |
 | 0x00411064 | -32684(gp) | printf |
 
 There we go, much better. Now that we know how to parse the address, we can see that `0x411064` refers to our friend `printf`. Also, a nice detail is that the access column corresponds to the original `addi` we used in order to load the address into our `$t9` register:
 ```asm
 	4007e0:		lw	v0,-32684(gp)
	4007e4:		move	t9,v0
	4007e8:		jalr	t9
```

If so, this simple piece of code can be translated into:
```c
printf("Please, enter a password : ");
```

Moving forward, We'll assume we know how to parse function calls and string references, as per this lengthy walkthrough.

#### 0x4007f0 - 0x400810
```asm
	  4007f0:	lw	gp,16(s8)
	  
	  4007f4:	addiu	v0,s8,36
	  4007f8:	move	a1,v0
	  4007fc:	lui	v0,0x40
	  400800:	addiu	a0,v0,2828
	  400804:	lw	v0,-32704(gp)
	  400808:	move	t9,v0
	  40080c:	jalr	t9
	  400810:	nop
```
The first instruction here restores `$gp` from the stack, where we stored it in the prolouge. (This is in case it was clobbered by the `printf` call)

This lovely piece of code simply calls one function from the standard library with 2 arguments, `$a0` and `$a1`.
Since we already know how to extract the called function from this code, we can easily find that we are in fact calling `__isoc99_scanf`, which is basically just [`scanf`](https://www.tutorialspoint.com/c_standard_library/c_function_scanf.htm). 

`scanf` takes a format string and a pointer to a buffer on which to store a string from standard input into (while parsing it using our supplied format string).

Let's parse the arguments.

* `$a0` is again refercing memory inside the `.rodata` section, and we can use the string table we've constructed to find that it is in fact referecing the string `"%10s"`, which makes sense as it is indeed a format string, taking a 10-character (maximum) string.
* `$a1` is pointed at `$s8+36`, which is equivelant to `$sp+36`. From the signature of `scanf` we can tell that this is in fact the address to which our string will be saved.

From this piece of code, we've learned that the C implementation most likely includes the following lines:
```c
char buf[10]; // This variable is found at $sp+36
scanf("%10s", &buf);
```
Awesome. We are slowly piecing together this code.

#### 0x400814 - 0x400828
```asm
	400814:	lw	gp,16(s8)
	
	400818:	sw	v0,32(s8)
	40081c:	lw	v1,32(s8)
	400820:	li	v0,1
	400824:	beq	v1,v0,400850 <main+0xb0>
	400828:	nop
```
This code does not look like a function call.
We already recognize the first line as restoring `$gp`, so we can safely ignore it.

We are left with a comparison. The first two lines are just moving v0 to v1 while also storing the value on the stack.
We know `$v0` contains the return value for the last subroutine call, and since that call was `scanf` we can look at the reference (`man scanf`) to find that it returns:
```
RETURN VALUE
       On success, these functions return the number of input items successfully  matched
       and assigned; this can be fewer than provided for, or even zero, in the event of an
       early matching failure.

       The value EOF is returned if the end of input is reached before  either  the  first
       successful conversion or a matching failure occurs.  EOF is also returned if a read
       error occurs, in which case the error indicator for the stream (see  ferror(3))  is
       set, and errno is set to indicate the error.
```
Basically, it should return the number of strings matched, which from our format string we expect to be 1. When no error occured, we expect `$v0` to be 0x1 at the beginning of this code segment. If so, `$v1` is now also 0x1.

At `0x400820`, we load the value 0x1 into `$v0`, after it's previous value was transferred to `$v1`.
The next instruction simply compares the two and branches accordingly. We know that success in this case means equality, so  we know that if we branch here, `scanf` succeeded and we got a string from the user.

In order to follow the logical flow of the program, we will now jump to the address specified by the branch, and assume a string has been given to the program.

#### 0x400850 - 0x40086c
```asm
	400850:	li	a0,10
	400854:	lw	v0,-32700(gp)
	400858:	move	t9,v0
	40085c:	jalr	t9
	400860:	nop

	400864:	lw	gp,16(s8)
	400868:	b	40089c <main+0xfc>
	40086c:	nop
```
This code is made up of 2 distinct pieces.

The first one is a standard library function call to `putchar`, which prints a char to `stdout`. (AKA The Console*)
In this case:
```c
putchar(0xa); // 0xa is '\n'
```
This is basically just a newline print.
###### * The console actually interfaces with the program's `stdout` and reads from it, rather than the console actually being `stdout`.

The second piece restores `$gp` and branches (unconditionally) to `0x40089c`. Let's follow the flow of the program.

#### 0x40089c - 0x4008b0
```asm
	40089c:	lw	v0,24(s8)
	4008a0:	addiu	v1,s8,24
	4008a4:	addu	v0,v1,v0
	4008a8:	lb	v0,12(v0)
	4008ac:	bnez	v0,400870 <main+0xd0>
	4008b0:	nop 
```
The next piece of code may seem complicated at first, but looking through it a few times carefully can really help.
Let's try to illustrate this code in C:
```c
v0 = *($sp+24);
v1 = $sp+24;
v0 = v0 + v1;
v0 = (int)(*(v0+12));

if (v0 != 0)
	goto 0x400870
```
Not very helpful is it... Well there's still some things we can do in order to parse this code. Let's try to look at the stack. 

From the prolouge, we know that `24(sp)` is zeroed out, and since we haven't touched it anywhere since it should stay that way. We also know that `36(sp)` stores our string. This will probably come in handy. If these are true, `24(sp)` being loaded into `$v0` in fact zeroes it out. We also see that the address `sp+24` is moved to `$v1`.

The next thing that happens may take a moment to parse, but in fact it is:
```c
v0 = (int)(*(v1+v0+12));
```
Right now, we know that `$v0` is in fact 0, and that `$v1` contains the address `sp+24`. If so, that means we are doing the following:
```c
v0 = (int)(*(sp+24+12));
```
Oh wait! We know exactly what is stored at `$sp+36`... It is our string!
If so, that means we are in fact loading the first character from our string into `$v0` from the stack.

The next instruction simply compares our byte to `\x00`, the null terminator, and branches back to the address `0x400870` as long as the byte loaded is not the null-terminator.

Just by looking at this piece of code, we can maybe catch a vibe of what it's trying to do. But if we still don't know, we can just keep following the code in order to find out.

#### 0x400870 - 0x4008b0
```asm
	400870: lw	v0,24(s8)
	400874: addiu	v1,s8,24
	400878: addu	v0,v1,v0
	40087c: lb	v0,12(v0)
	
	400880: move	v1,v0
	
	400884: lw	v0,28(s8)
	400888: addu	v0,v0,v1
	40088c: sw	v0,28(s8)
	
	400890: lw	v0,24(s8)
	400894: addiu	v0,v0,1
	400898: sw	v0,24(s8)

	40089c: lw	v0,24(s8)
	4008a0: addiu	v1,s8,24
	4008a4: addu	v0,v1,v0
	4008a8: lb	v0,12(v0)
	
	4008ac: bnez	v0,400870 <main+0xd0>
	4008b0: nop
```
Before examining the next piece of code, please notice that I've kept in the last piece of code we've analyzed, for reasons that should become clear momentairly.

The first piece of code here seems to be a replication of the last piece of code that we've just analyzed. Why then would this code be duplicated? It's not like `$v0` or `$v1` changed since the last time this piece of code ran... This is an odd detail without seeing the bigger picture. But it is another hint as to the purpose of this code.

The next instruction moves `$v0` to `$v1`. This means that both `$v0` and `$v1` now contain the loaded character. The next set of instructions can be simplified to the following pseudo-code:
```c
*($sp+28) += $v1
```
We are adding `$v1` to a location in memory. Because of the RISC philosophy, we have to use an intermediate register in order to perform the operation.
What this basically means is that we're adding the char we loaded to the value stored at `28(sp)`

The next set of instructions, which is the last new batch, can also be simplified as such:
```c
*($sp+24) += 1
```
Which is basically just incrementing the value stored at `24(sp)`.

And then we get back to the same set of instructions we've already analyzed, loading a char into `$v0`. Only this time, since we've added 0x1 to the zero value stored in `24(sp)`, The operation will reference the next char in the string, as follows:
```c
v0 = (int)(*(v1+v0+12));
```
Which is equal to roughly:
```c
v0 = (int)(*(sp+37));
```
And so, as long as we haven't reached a null terminator, we will keep **looping** over the string we got as input and perform the following operations:
```c
int i; # 24(sp)
int sum; # 28(sp)
char buf[10]; 36(sp)

while ( buf[i] != 0 ){
	sum = sum + buf[i];
	i++;
}
```

Alright! We're almost there!

Let's look at the instructions immediately following the `bnez`. As soon as we've reached the end of the string, we will continue execution and reach the next piece of code.

#### 0x4008b4 - 0x4008c0
```asm
	4008b4:	lw	v1,28(s8)
	4008b8:	li	v0,1337
	4008bc:	bne	v1,v0,4008e8 <main+0x148>
	4008c0:	nop
```
This piece of code is significant. Note that we've already marked `28(sp)` as `sum`, which is the sum of all the characters in our string. We can clearly see then that this branch is comparing our sum to `1337` (L33T). If our `sum` does not match the magic number, we branch to `0x4008e8`. Let's assume for a moment that we've somehow reached the magic number. If so, we execute the following piece of code next:

#### 0x4008c4 - 0x4008e4
```asm
	4008c4:	lui	v0,0x40
	4008c8:	addiu	a0,v0,2860
	4008cc:	lw	v0,-32688(gp)
	4008d0:	move	t9,v0
	4008d4:	jalr	t9
	4008d8:	nop

	4008dc:	lw	gp,16(s8)
	4008e0:	b	400904 <main+0x164>
	4008e4:	nop
```
The last piece of code simply restores `$gp` and branches unconditionally to `0x400904`.

It's the first piece of code that we're interested in here. If we take a look at the function reference table that we've constructed, we can see that we're calling `puts` here. It's the argument we're passing I'm most interested in, in this case. Constructing the address and matching it against our string table will inform us that the string passed to puts is, drumroll please:

"correct password! "

**Bingo.**

Now that we've figured out how to get to our desired outcome, let's quickly reconstruct the original C code.

### Source
I've filled in the parts we haven't analyzed, such as the "wrong password! " print and some other minor details.
```c
int main(){
	int i;
	int sum;
	char buf[10] = {0}; // Zeroing out the buffer

	printf("Please, enter a password : ");
	ret = scanf("%10s", &buf);
	if (ret == 1){
		while ( buf[i] != 0 ){
			sum = sum + buf[i];
			i++;
		}
		if (sum == 1337){
			puts("correct password! ");
		}
		else{
			puts("wrong password! ");
		}
	}
	else {
		puts("no password entered! ");
	}
return ret;
}
```

OK. Now that we know what the code is doing, we can get to solving it.

## Solution

Alright. So what do we know?

* We have an executable that's taking 10 characters
* It is then summing those characters
* Lastly, the sum is compared to `1337`.

If so, the solution should be simple. The sort of attack we are about to implement is called a "Hash Collision Attack", where in an attacker constructs a string such that running a specific hash function on it generates a desirable value. In this case, the hash function simply sums the characters, and the desired value is `1337`.

Great. In this case, we can simply divide our sum of `1337` over the number of characters, and solve it that way.
```python
sum = 1337
character = 1337 // 10
last_char = character + (1337 % 10)
if 1337 == (character * 9) + last_char: # If we actually have the right string
	print(repr((chr(character) * 9) + chr(last_char))) # Print the hex representation.
```
And if we run the code, we get the following string:
```
\x85\x85\x85\x85\x85\x85\x85\x85\x85\x8c
```
Awesome. Now let's plug it to our program using `echo`:
```console
user@pc$ echo -n -e "\x85\x85\x85\x85\x85\x85\x85\x85\x85\x8c" | sudo chroot . qemu-mips-static bin/challenge3
Please, enter a password : 

wrong password! 
```
Wait, what?

Maybe there's something wrong with our calculations? Well, going over them leaves no room for wondering, nothing is wrong with our calculations. Something else must be at play here.

If we can't solve it just by staring at the code until it confesses, we can do the next best thing. Let's use `gdb` in order to see what's happening here.

### Debugging with GDB
In order to debug a `qemu` program, we need to run it with `-g` and supply a port so that it can server it's `gdb-server`.
We can do this like so:
```console
user@pc$ echo -n -e "\x85\x85\x85\x85\x85\x85\x85\x85\x85\x8c" | sudo chroot . qemu-mips-static -g 12345 bin/challenge3
```
In a separate console we can then do:
```console
user@pc$ gdb-multiarch bin/challenge3
...
...
(gdb) set arch mips
(gdb) set endian big
(gdb) target remote localhost:12345
```
We're in. Now we can take a look at the program using `gdb`'s facilities. We can disassemble the `main` function using
```console
(gdb) disas main
```
Which will spit the assembly for the function. We already know where our important comparison happens, so we can start by setting a breakpoint there:
```console
(gdb) b *0x004008bc
```
Alright. Now let's run with `c` and reach the breakpoint. Once we've reached our breakpoint, we can start to investigate.
Let's take a look at the original assembly again:
```asm
	4008b4:	lw	v1,28(s8)
	4008b8:	li	v0,1337
	4008bc:	bne	v1,v0,4008e8 <main+0x148>
	4008c0:	nop
```
So at `0x004008bc`, we know that the value for our sum (saved at `28(sp)`), should be loaded into `$v1`. We also know that `0x539`, which is equal to `1337`, should be loaded into `$v0`.

Right, so now we can look at the registers in order to see what the values are. Let's use `info registers`.
```console
(gdb) info registers
          zero       at       v0       v1       a0       a1       a2       a3
 R0   00000000 00000001 00000539 fffffb39 7f7c4e2c ffffffff 00000001 00000000 
            t0       t1       t2       t3       t4       t5       t6       t7
 R8   7f6a2840 00000000 00000b64 7f7fe300 00000001 7f643ff8 7f63a918 00000486 
            s0       s1       s2       s3       s4       s5       s6       s7
 R16  00000000 00400920 00000000 00000000 00000000 00000000 00000000 00000000 
            t8       t9       k0       k1       gp       sp       s8       ra
 R24  00000000 7f73e930 00000000 00000000 00419010 7ffff668 7ffff668 00400864 
            sr       lo       hi      bad    cause       pc
      20000010 0001f324 00000216 00000000 00000000 004008bc 
           fsr      fir
      00000000 00739300 
```
And here we have are values.

`$v0` is `0x539` as expected, and `$v1` is also - Wait what? `0xfffffb39`? Where did this value come from?
Strange...

Let's try to understand what happened here. Let's restart and put a breakpoint right after the first `lb` instruction to see what byte is loaded into memory.

```console
(gdb) b *0x4008ac
(gdb) c
```
Now that we've reached the breakpoint, let's look at the registers again.
```console
(gdb) info registers
          zero       at       v0       v1       a0       a1       a2       a3
 R0   00000000 00000001 ffffff85 7ffff680 7f7c4e2c ffffffff 00000001 00000000 
            t0       t1       t2       t3       t4       t5       t6       t7
 R8   7f6a2840 00000000 00000b64 7f7fe300 00000001 7f643ff8 7f63a918 00000486 
            s0       s1       s2       s3       s4       s5       s6       s7
 R16  00000000 00400920 00000000 00000000 00000000 00000000 00000000 00000000 
            t8       t9       k0       k1       gp       sp       s8       ra
 R24  00000000 7f73e930 00000000 00000000 00419010 7ffff668 7ffff668 00400864 
            sr       lo       hi      bad    cause       pc
      20000010 0001f324 00000216 00000000 00000000 004008ac 
           fsr      fir
      00000000 00739300 
``` 
Now we can see that the value of `$v0` is `0xffffff85`. Why is `$v0` getting this value, and not just `0x85`? Let's try feeding our program some other character, maybe `A`s wil work.
```console
user@pc$ echo -n -e "AAAAAAAAAA" | sudo chroot . qemu-mips-static -g 12345 bin/challenge3
```
By getting to the same breakpoint, we can look at the registers again:
```console
(gdb) info registers
          zero       at       v0       v1       a0       a1       a2       a3
 R0   00000000 00000001 00000041 7ffff680 7f7c4e2c ffffffff 00000001 00000000 
            t0       t1       t2       t3       t4       t5       t6       t7
 R8   7f6a2840 00000000 00000b64 7f7fe300 00000001 7f643ff8 7f63a918 00000486 
            s0       s1       s2       s3       s4       s5       s6       s7
 R16  00000000 00400920 00000000 00000000 00000000 00000000 00000000 00000000 
            t8       t9       k0       k1       gp       sp       s8       ra
 R24  00000000 7f73e930 00000000 00000000 00419010 7ffff668 7ffff668 00400864 
            sr       lo       hi      bad    cause       pc
      20000010 0001f324 00000216 00000000 00000000 004008ac 
           fsr      fir
      00000000 00739300 
```
This time, `$v0` is indeed getting the currect hex value for `A`, which all of us pwners know well by now is `0x41`.

OK. What in the world is happening then? This took a few minutes to figure out, but then it hit me: **Sign extension!**

In order to explain the term sign extension, we first need to look at the term **2's Complement**. In short, 2's complement is a method of storing negative numbers in binary form. If you remember, we've discovered back at our very first `readelf` that this program uses the 2's complement method, because of the MIPS architecture.


#### 2's complement
Let's say we have a byte, which can store 256 values. Instead of storing 0 to 255 and an additional sign bit, we can declare that the values stored in the byte will range from 127 to -128, and since this is still only a range of 256 numbers, we can still cram all those values in.

The actual implementation of the 2's complement method can be read upon [here](https://en.wikipedia.org/wiki/Two%27s_complement), but for now suffice it to say we have shifted the range of possible values such that `0x1 - 0x7f` represent positive numbers and `0xff - 0x80` represent negative numbers.

And so, if that is the case, this still does not explain the `0xffffff` appended to our value of `0x85`. This is where sign extension comes in.
#### Sign extension
Extension referes to the process of loading a number represented by a number of bits into a register or location where it is represented by a larger number of bits. Let's say we load a byte into a 16-bit register. We already know what to put in the least significant 8 bits, but what do we do with the high bits?

Well, there are two options:

* Zero extension - Filling the rest of the bits with 0, and possibly losing sign information when using the 2's complement method. By zero extension, we are in fact treating the value as an unsigned value.
* Sign extension - The alternative method is filling the rest of the bits with sign-matching bits: if the number is negative, fill them with `1` bits. If the number is positive, fill them with `0`.

In order to understand why exactly this happens it is recommended to know how 2's complement works, and as such I should recommend again that you read into it [here](https://en.wikipedia.org/wiki/Two%27s_complement). This writeup has already become too long for me to delve into the topic.

For now though, we know that `0x85` is a negative value, and as such, sign extending it to 32 bits will indeed give us `0xffffff85`. On the opposite side, `0x41` is positive, and sign extending it will give us the same `0x00000041` value.

### What now then?
Well, if the values are indeed signed, and the maximum value of a byte is 127, that means that no matter what we try, we can only reach a maximum value of `127 * 10 = 1270 < 1337`.

Hmmm.

I've tried to think of other ways. Maybe a buffer overflow, maybe using LD_PRELOAD, same as the last challenge, something that can give us a way. LD_PRELOAD is not a valid solution, according to the challenge creator, and no buffer overflows or otherwise can work on this, I've tried.

**If so, the only option is to start modifying things. We'll start by simple modifications to the binary, and our last solution will be tampering with memory at runtime in order to avoid the patching of the binary.**

Now that the rules are clearly laid out, we can start coming up with soltuions. In order for the patching to not get quickly out of hand, I tried to limit myself to patching **only a single bit** in order to get the program to work with each solution.

### Workaround 1: Patching the `lb` instruction
We've already figured out that the fact the thae `lb` instruction sign-extends the registers. What if we could find a way to make the instruction load the byte into the register zero-extended? In fact, there is a very simple way of achieving that. If only we used a `lbu` (Load Byte Unsigned) instruction, all our issues will go away.

Luckily, in order to turn a `lb` into a `lbu`, all we have to do is simply flip one bit, turning the first byte from `0x80` to `0x90`.

If we look at the original instruction:
```asm
0x40087c:	80 42 00 0c	lb v0,12(v0)
```
We can see that simply patching it with a hex editor (010 Editor comes to mind), will turn it into a `lbu` instruction.
```asm
0x40087c:	90 42 00 0c	lbu v0,12(v0)
```
And that's it. It's that simple.

### Workaround 2: Patching the format string
Another possible solution is patching the format string being passed to `scanf`. Right now, we can only accept 10 characters. The sum of those signed chars will not surpass `1270` no matter what we do. But if we can instead accept more characters, say for example 11, we can increase the maximum value all the way up to `1397`, which safely includes the desired `1337` value. Luckily, we can do this without clobbering the stack, as there is enough allocated and unused space for an extra character.

Let's look at the format string in hex:
```
"%10s": 0x2531307300 == 25 31 30 73 00
```
We can simply change the char corresponding to the `0`, in this case `0x30`, to another `1` - `0x31`.
```
"%11s": 0x2531317300 == 25 31 31 73 00
```
This patching only constitutes a one bit change. That's it. Now, passing an 11 character string with chars within the signed range can get us the desired result.

### Workaround 3: Patching the constant
One obvious solution - If the constant is too big to reach, change the constant. We can patch the `0x539` (1337) to a `0x439` by simply changing one bit in the `li` instruction.

That means the following instruction:
```asm
0x4008b8:	24 02 05 39 	li v0,1337
```
Transforms into the following:
```asm
0x4008b8:	24 02 04 39 	li v0,1081
```
And now, we can easliy construct a colliding string.

### Workaround 4: Patching the branch
If we can't get to the right hash, why not make all the wrong hashes work instead? By changing one bit, and one bit only, we can patch the `bne` instruction and replace it with a `beq`. We've negated the `if` condition, and it's as simple as that.

If so, that means this instruction:
```asm
0x4008bc:	14 62 00 0a 	bne v1,v0,4008e8 <main+0x148>
```
Turns into the following:
```asm
0x4008bc:	10 62 00 0a 	beq v1,v0,4008e8 <main+0x148>
```
And we've eliminated any need to even try and match the password.

## Dynamic Memory Patching - Workaround 5

Now, patching the executable is all good an dandy, but I wanted to see if this could be done without patching. I was pointed towards `/proc/[pid]/mem`, and I started trying to figure out how that could be manipulated.

`/proc/[pid]/mem` allow the user direct access to a program's memory. Reading from the pseudo-file at offset `x` will read offset `x` of the program. Unfortunately, since this file is not modifiable, we can not use that for our purposes. At least, not on it's own.

Keep in mind that a process wishing to read this file for a specific `pid`, will have to first attach using `ptrace` to the process whose memory is being read.

### Using `/proc/[pid]/maps`
The following snippet was text was lifted straight from a StackOverflow answer by user `Gilles 'SO- stop being evil'` ([Link](https://unix.stackexchange.com/a/6302))

#### `/proc/$pid/maps`
`/proc/$pid/mem` shows the contents of $pid's memory mapped the same way as in the process, i.e., the byte at offset x in the pseudo-file is the same as the byte at address x in the process. If an address is unmapped in the process, reading from the corresponding offset in the file returns `EIO` (Input/output error). For example, since the first page in a process is never mapped (so that dereferencing a `NULL` pointer fails cleanly rather than unintendedly accessing actual memory), reading the first byte of `/proc/$pid/mem` always yield an I/O error.

The way to find out what parts of the process memory are mapped is to read `/proc/$pid/maps`. This file contains one line per mapped region, looking like this:
```
08048000-08054000 r-xp 00000000 08:01 828061     /bin/cat
08c9b000-08cbc000 rw-p 00000000 00:00 0          [heap]
```
The first two numbers are the boundaries of the region (addresses of the first byte and the byte after last, in hexa). The next column contain the permissions, then there's some information about the file (offset, device, inode and name) if this is a file mapping. See the [proc(5)](http://www.kernel.org/doc/man-pages/online/pages/man5/proc.5.html) man page or [Understanding Linux `/proc/id/maps` for more information](https://stackoverflow.com/questions/1401359/understanding-linux-proc-id-maps).

Here's a proof-of-concept script that dumps the contents of its own memory.
```python
#! /usr/bin/env python
import re
maps_file = open("/proc/self/maps", 'r')
mem_file = open("/proc/self/mem", 'r', 0)
for line in maps_file.readlines():  # for each mapped region
    m = re.match(r'([0-9A-Fa-f]+)-([0-9A-Fa-f]+) ([-r])', line)
    if m.group(3) == 'r':  # if this is a readable region
        start = int(m.group(1), 16)
        end = int(m.group(2), 16)
        mem_file.seek(start)  # seek to region start
        chunk = mem_file.read(end - start)  # read region contents
        print chunk,  # dump contents to standard output
maps_file.close()
mem_file.close()
```

#### `/proc/$pid/mem`
If you try to read from the mem pseudo-file of another process, it doesn't work: you get an `ESRCH` (No such process) error.

The permissions on `/proc/$pid/mem` (r--------) are more liberal than what should be the case. For example, you shouldn't be able to read a setuid process's memory. Furthermore, trying to read a process's memory while the process is modifying it could give the reader an inconsistent view of the memory, and worse, there were race conditions that could trace older versions of the Linux kernel (according to this [lkml](http://lkml.indiana.edu/hypermail/linux/kernel/0505.0/0858.html) thread, though I don't know the details). So additional checks are needed:

The process that wants to read from `/proc/$pid/mem` must attach to the process using ptrace with the `PTRACE_ATTACH` flag. This is what debuggers do when they start debugging a process; it's also what `strace` does to a process's system calls. Once the reader has finished reading from `/proc/$pid/mem`, it should detach by calling ptrace with the PTRACE_DETACH flag.
The observed process must not be running. Normally calling `ptrace(PTRACE_ATTACH, …)` will stop the target process (it sends a `STOP` signal), but there is a race condition (signal delivery is asynchronous), so the tracer should call `wait` (as documented in [ptrace(2)](http://www.kernel.org/doc/man-pages/online/pages/man2/ptrace.2.html)).
A process running as root can read any process's memory, without needing to call ptrace, but the observed process must be stopped, or the read will still return `ESRCH`.

In the Linux kernel source, the code providing per-process entries in `/proc` is in `fs/proc/base.c`, and the function to read from `/proc/$pid/mem` is `mem_read`. The additional check is performed by [`check_mem_permission`](http://lxr.linux.no/#linux+v2.6.37/fs/proc/base.c#L197).

Here's some sample C code to attach to a process and read a chunk its of mem file (error checking omitted):
```c
sprintf(mem_file_name, "/proc/%d/mem", pid);
mem_fd = open(mem_file_name, O_RDONLY);
ptrace(PTRACE_ATTACH, pid, NULL, NULL);
waitpid(pid, NULL, 0);
lseek(mem_fd, offset, SEEK_SET);
read(mem_fd, buf, _SC_PAGE_SIZE);
ptrace(PTRACE_DETACH, pid, NULL, NULL);
```
### Parsing the memory
Now that we know what `/proc/[pid]/maps` can do for us, we can use it in order to read the contents of the program. While initially solving this, I was using a helper C program I wrote (Can be found in `utils`). Using this program I could attach to the process and read memory at arbitrary locations, while it was attached to and running in the background.

After writing a script, I know I easily could have used `Python` to have done so, using the proof-of-concept script presented in the answer above. Using that script to read the memory allows us to search it using `re` (Python's regex implementation), which can allow us to find patterns in the memory.

One way of using this to our advantage is filling the password buffer with `A`s, and subsequently searching for them in the memory.

### Physical Memory, Virtual Memory amd Virtual Virtual Memory
We need to stop here for a moment. There is one important detail that I've been omitting up until now: **The addresses we are accessing and reading are not the same addresses that we can find by using GDB**. The reason for that is quite simple. Since we're using an emulator, it has its own memory regions, living in the 64-bit virtual realm of our computer (Only our kernel can access physical memory addresses directly), and this emulator has to then emulate a virtual address space for our MIPS program to run in, hence the "Virtual Virtual" name.

Knowing that still doesn't explain how GDB can access this memory as if it were completely normal, and the reason for that is that since we attached to the program through a GDB Server instance provided to us by QEMU (`-g 12345`), all of the access to memory goes through a translator that allows GDB to treat the program's address space as if it was running normally on a MIPS setup.

Knowing this explains why we have to scan the memory for our `"A"s` buffer, since with our computer using [ASLR](https://en.wikipedia.org/wiki/Address_space_layout_randomization) and virtualizing the memory space for the emulated executable, the buffer will change locations every run and we will have to relocate it.

### Bruteforcing the emulator
Now that we've found our buffer, we will encounter some fascinating thing: Our string can be found twice in memory! Reading forwards and backwards in those memory locations reveals that one of the strings is found within the console buffer, which I find amusing but also distractive for our script. We'll have to handle finding the right address (See the script for solution. Long story short: it's always the second one).

Now the only way I could find to ensure that the desired location in the memory is indeed `0x539` when it is tested is to single-step the emulator using `ptrace` and poke the value into the desired address with every iteration. Yes, you heard me right. Single-step the emulator, not the program. One can only imagine how many emulator instructions it takes to run a single emulated instruction, and by doing it this way we are killing every hope we had at a preformant program. Solving it this way takes around 20 seconds of runtime, which is unbelievable for a program which does basically nothing.

With all that said, it works.

It was very tiring to get there, but it does indeed work.

##### Full dynamic solution can be found in the `solution5` folder in the repo.

## Last words
That's it. We've done it. We've solved the challenge, we overcame the issue. We learned from it, we grew from it.

If you read all the way to here, I want to believe you at least found something useful or interesting in this guide. I encourage you to look at the solutions and try them for yourself.
Any inquiries about the solutions will be happily accepted in any communication channel you can reach me at.

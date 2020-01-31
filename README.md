# CyberChallenge0x03

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
###### For a detailed explanation on `chroot` please refer to my solution for the previous challenge, found [here](https://github.com/ThatFatPat/CyberChallenge0x02)

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

### First Run
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
| $30 | $fp (or $s8) | The Frame Pointer |
| $31 | $ra | The Return Address in a subroutine call. |

###### Adapted from UW CSE410 ([Source](https://courses.cs.washington.edu/courses/cse410/09sp/examples/MIPSCallingConventionsSummary.pdf))



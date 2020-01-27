import re
from subprocess import check_output
import struct
import codecs
codecs.register_error("strict", codecs.ignore_errors)

import ctypes
import sys
import os

PTRACE_POKEDATA   = 5
PTRACE_SINGLESTEP = 9
PTRACE_ATTACH     = 16
PTRACE_DETACH     = 17


def get_pid(name):
	try:
		return check_output(["pidof",name])
	except Exception:
		print("Please run the program first!")
		sys.exit(1)

def get_address(pid):
	maps_file = open("/proc/%d/maps"%pid, 'r')
	mem_file = open("/proc/%d/mem"%pid, 'rb')
	read_mem = []
	addresses = []

	# Read all of the memory contents into an array of (data, offset) where offset is the base offset for the attached data.
	# For example ("AAAAB", 0x0005) means we can find a "B" in memory at address 0x5 + 0x4 = 0x9
	for line in maps_file.readlines():  # for each mapped region
		try:
			m = re.match(r'([0-9A-Fa-f]+)-([0-9A-Fa-f]+) ([-r])', line)
			if m.group(3) == 'r':  # if this is a readable region
				start = int(m.group(1), 16)
				end = int(m.group(2), 16)
				mem_file.seek(start)  # seek to region start
				chunk = mem_file.read(end - start)  # read region contents
				read_mem.append((chunk, start))  # dump contents to standard output
		except Exception:
			continue
	maps_file.close()
	mem_file.close()

	# Find all matches of 'AAAAAAAAAA' in memory and return the address adjusted for the offset.
	possible = [[m.start()+off for m in re.finditer(b'AAAAAAAAAA', chk)] for chk, off in read_mem]
	for lst in possible:
		for str_addr in lst:
			# The structure of the stack dictates the string is saved at $sp+0x24 and the sum is at $sp+0x1c. 0x24-0x1c = 8
			addresses.append(str_addr - 8)
		
	return addresses

def main():
	libc = ctypes.CDLL('/lib/x86_64-linux-gnu/libc.so.6') # Your libc location may vary!
	libc.ptrace.argtypes = [ctypes.c_uint64, ctypes.c_uint64, ctypes.c_void_p, ctypes.c_void_p]
	libc.ptrace.restype = ctypes.c_uint64

	pid = int(get_pid("qemu-mips-static")[:-1])
	address = 0
	addresses = []

	libc.ptrace(PTRACE_ATTACH, pid, None, None)



	# Ignore these variables, they are just here to print things neatly
	started_work_print = False
	found_address_print = False
	only_print_address_once = True


	# os.waitpid returns (pid, status_number), where status_number is the signal sent from the process as for the reason we got back control.
	stat = os.waitpid(pid, 0)
	count = 0
	while not os.WIFEXITED(stat[1]):

		# Print info
		if started_work_print:
			print("Started cracking the program. Please be patient!")
			started_work_print = False
		if found_address_print:
			print(f"Found address of sum: {hex(address)}")
			found_address_print = False
		# End print


		# Actual loop
		if os.WIFSTOPPED(stat[1]):

			if os.WSTOPSIG(stat[1]) == 19: # If we got here because of a PTRACE_ATTACH
				print("Attached to process!")
				print(f"PID: {pid}")
				started_work_print = True
			
			elif len(addresses) > 1: # Else if we know what address to write to
				libc.ptrace(PTRACE_POKEDATA, pid, address, 0x39050000)
			
			# Single step the program to the next instruction
			libc.ptrace(PTRACE_SINGLESTEP, pid, None, None)

		""" Since we have no way of accesssing pc, we try to get the address every 2000000 iterations until we find our string on the stack. 
		After that, we ensure that with every instruction the value at that address is exactly 0x539, so that the comparison passes."""

		if count % 2000000 == 0:
			if len(addresses) < 2: # The password string is saved twice in memory, once for the console and once on the stack. The second address is always the stack.
				addresses = get_address(pid)
				address = addresses[1] if len(addresses) > 1 else 0

			# Printing related
			elif only_print_address_once:
				found_address_print = True
				only_print_address_once = False
			# End printing related
		
		# Next iteration
		count += 1 
		stat = os.waitpid(pid, 0)


	libc.ptrace(PTRACE_DETACH, pid, None, None)

if __name__ == "__main__":
	main()
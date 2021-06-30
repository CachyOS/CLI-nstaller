import json
import logging
import os
import time
import subprocess
import sys

try:
	import httplib
except:
	import http.client as httplib

import archinstall
from archinstall.lib.general import run_custom_user_commands
# from archinstall.lib.hardware import has_uefi, AVAILABLE_GFX_DRIVERS
from archinstall.lib.hardware import *
from archinstall.lib.networking import check_mirror_reachable
from archinstall.lib.profiles import Profile

cachy_offline = False

essentials = ["vi", "nano", "fish", "bash-completion"]

cachyos_gpg_key_url = "https://raw.githubusercontent.com/CachyOS/PKGBUILDS/master/keyring-cachyos/cachyos.gpg"
cachyos_packages = "linux-cachyos linux-cachyos-headers "
cachyos_kde_theme = "cachyos-kde-theme "

minimum_kde_packages =	["xorg", "plasma-desktop", "plasma-framework", "plasma-nm", "plasma-pa",
			"konsole", "kate", "dolphin", "sddm", "sddm-kcm", "ttf-opensans"]

rec_kde_packages =	["bluedevil", "drkonqi", "kde-gtk-config", "kdeplasma-addons",
			"khotkeys", "kinfocenter", "kscreen", "ksshaskpass",
			"plasma-systemmonitor", "plasma-thunderbolt", "powerdevil",
			"kwayland-integration", "kwallet-pam", "kgamma5", "breeze-gtk",
			"xdg-desktop-portal-kde", "gwenview", "okular", "spectacle",
			"dragon", "elisa", "ark", "gnome-calculator", "htop",
			"tree"]

full_kde_packages =	["plasma-meta", "kde-applications-meta"]

# Browsers
browser = ["firefox"]

# Graphics Drivers
Xorg_Intel_pa = ["xf86-video-intel"]
Nouveau_pa = ["xf86-video-nouveau"]
Xorg_amdgpu_pa = ["xf86-video-amdgpu"]
Xorg_vmware_pa = ["xf86-video-vmare"]
Xorg_ati_pa = ["xf86-video-ati"]
Xorg_vesa_pa = ["xf86-video-vesa"]
Xorg_Openchrome_pa = ["xf86-video-openchrome"]
Nvidia_pa = ["nvidia", "nvidia-settings", "nvidia-utils"]

class bcolors:
	HEADER = '\033[95m'
	OKBLUE = '\033[94m'
	OKCYAN = '\033[96m'
	OKGREEN = '\033[92m'
	YELLOW = '\033[93m'
	RED = '\033[91m'
	GRAY = '\033[1;37m'
	ORANGE = '\033[33m'
	BLACK = '\033[30m'
	BG_WHITE = '\033[47m'
	ENDC = '\033[0m'
	BOLD = '\033[1m'
	UNDERLINE = '\033[4m'

if archinstall.arguments.get('help'):
	print("See `man archinstall` for help.")
	exit(0)
if os.getuid() != 0:
	print("Archinstall requires root privileges to run. See --help for more.")
	exit(1)


if len(sys.argv) > 1 and sys.argv[1] == "--semi-offline":
	cachy_offline = True
	print(bcolors.GRAY + "mode: " + sys.argv[1] + bcolors.ENDC)

def print_cachyos_banner():
	cachyos_banner = subprocess.run(['figlet', '     CachyOS'], stdout=subprocess.PIPE)
	print(chr(27) + "[2J")
	print(cachyos_banner.stdout.decode('utf-8'))
	print(bcolors.OKCYAN + bcolors.BLACK + "     --------------", end="")
	print(bcolors.RED + "--------------", end="")
	print(bcolors.YELLOW + "--------------" + bcolors.ENDC)

	print("\nWelcome to the CachyOS installer")

def show_iwctl():
	archinstall.log("Instructions to connect to wifi using iwclt:", fg="yellow")
	archinstall.log("\t1- when iwclt opened, type `station list`", fg="yellow")
	archinstall.log("\t2- see your wifi device name ex. wlan0", fg="yellow")
	archinstall.log("\t3- type `station wlan0 scan`, and wait couple seconds", fg="yellow")
	archinstall.log("\t4- type `station wlan0 get-networks` (find your wifi Network name ex. my_wifi)", fg="yellow")
	archinstall.log("\t5- type `station wlan0 connect my_wifi` (don't forget to press TAB for auto completion!)", fg="yellow")
	archinstall.log("\t6- type `station wlan0 show` (status should be connected)", fg="yellow")
	archinstall.log("\t7- type `exit`", fg="yellow")

	input("Press Enter to continue to iwctl...")
	os.system("iwctl")

def check_internet_connectivity(nr_tries=1):
	print("\nChecking internet connectivity...")

	conn = httplib.HTTPConnection("www.google.com", timeout=5)
	try:
		conn.request("HEAD", "/")
		conn.close()
		archinstall.log("Connected to the Internet (OK)", fg="green")
	except:
		conn.close()
		if nr_tries == 1:
			nr_tries = 2
			print(bcolors.YELLOW + "It seems not connected! Waiting for 10s before trying again..." + bcolors.ENDC)
			time.sleep(10)
			check_internet_connectivity(nr_tries)
			return

		archinstall.log("Not connected to the Internet!, please check!", fg="red")
		print(bcolors.YELLOW + "In case you are using wifi, do you want to connect to wifi? (y/n): " + bcolors.ENDC, end="")
		r = input()
		if r == "y" or r == "Y":
			show_iwctl()
			check_internet_connectivity()
		else:
			archinstall.log("You are exiting the installer. To run the installer again run/type `install_cachyos`", fg="yellow")
			archinstall.log("Exiting...")
			exit()


def print_margin():
	t_size = os.get_terminal_size().lines
	for i in range(t_size - 19):
		print()

print_cachyos_banner()
check_internet_connectivity()
print_margin()


# For support reasons, we'll log the disk layout pre installation to match against post-installation layout
archinstall.log(f"Disk states before installing: {archinstall.disk_layouts()}", level=logging.DEBUG)

separator_text = ""
total_steps = "9"
g_current_step = ""
def print_separator(current_step = ""):
	global separator_text
	global g_current_step

	if current_step:
		g_current_step = current_step

	if not separator_text:
		t_width = os.get_terminal_size().columns
		for i in range(t_width - 8):
			separator_text += "-"

	print(bcolors.GRAY + separator_text + " " + g_current_step + " / " + total_steps + bcolors.ENDC, flush=True)



def add_cachyos_keyring(installation):
	print(f"\n{bcolors.GRAY}Adding CachyOS keyring...\n{bcolors.ENDC}")
	os.system(f"wget {cachyos_gpg_key_url}")
	os.system(f"cp ./cachyos.gpg {installation.target}/usr/share/pacman/keyrings/cachyos.gpg")
	commands = [
		"gpg --import /usr/share/pacman/keyrings/cachyos.gpg",
		"pacman-key --add /usr/share/pacman/keyrings/cachyos.gpg",
		"pacman-key --finger C3C4820857F654FE",
		"pacman-key --lsign-key C3C4820857F654FE",
		"pacman-key --finger 49B94AEF35812D6C",
		"pacman-key --lsign-key 49B94AEF35812D6C",
		"pacman-key --populate"
	]
	run_custom_user_commands(commands, installation)

def add_cachyos_repo(installation):
	print(f"\n{bcolors.GRAY}Adding CachyOS Repository...\n{bcolors.ENDC}")
	_file = "/etc/pacman.conf"
	commands = [
		"sed -i 's/\[core\]/\[cachyos\]\\nSigLevel = Optional TrustAll\\nServer = https:\/\/cachyos.github.io\/cachyos_repo\/x86_64\\n\\n\[core\]/' " + _file,
		'pacman --noconfirm -Sy'
	]
	run_custom_user_commands(commands, installation)

def enable_services(installation):
	# check if kde is selected
	ins_sel = archinstall.arguments.get('installation_selection', None)
	if ins_sel and (ins_sel == "minimam KDE" or 
			ins_sel == "moderated KDE" or ins_sel == "full KDE"):
		try:
			# add sddm service if kde is isntalled
			installation.enable_service("sddm.service")
			# add NetworkManager service if kde is isntalled
			installation.enable_service("NetworkManager.service")
		except:
			pass


def install_selected_packages(installation):
	global cachyos_packages
	other_packages = []

	# check if kde is selected
	ins_sel = archinstall.arguments.get('installation_selection', None)
	if ins_sel:
		if ins_sel == "minimam KDE" or ins_sel == "moderated KDE" or ins_sel == "full KDE":
			cachyos_packages += cachyos_kde_theme

		if ins_sel == "minimam KDE":
			installation.add_additional_packages(minimum_kde_packages)
		if ins_sel == "moderated KDE":
			installation.add_additional_packages(minimum_kde_packages)
			installation.add_additional_packages(rec_kde_packages)
			other_packages = other_packages + browser
		if ins_sel == "full KDE":
			installation.add_additional_packages(minimum_kde_packages)
			installation.add_additional_packages(rec_kde_packages)
			installation.add_additional_packages(full_kde_packages)
			other_packages = other_packages + browser

	# add essentials
	other_packages = other_packages + essentials

	# add ucode
	if archinstall.arguments.get("ucode", None):
		other_packages = other_packages + [archinstall.arguments["ucode"]]

	# add graphics driver
	if archinstall.arguments.get("graphics_driver", None):
		graphics_driver = archinstall.arguments["graphics_driver"]

		if graphics_driver == "Xorg Intel":
			other_packages = other_packages + Xorg_Intel_pa
		elif graphics_driver == "Nouveau":
			other_packages = other_packages + Nouveau_pa
		elif graphics_driver == "Xorg AMD":
			other_packages = other_packages + Xorg_amdgpu_pa
		elif graphics_driver == "Xorg vmware":
			other_packages = other_packages + Xorg_vmware_pa
		elif graphics_driver == "Xorg ati":
			other_packages = other_packages + Xorg_ati_pa
		elif graphics_driver == "Xorg vesa":
			other_packages = other_packages + Xorg_vesa_pa
		elif graphics_driver == "Xorg Openchrome":
			other_packages = other_packages + Xorg_Openchrome_pa
		elif graphics_driver == "Xorg Nvidia":
			other_packages = other_packages + Nvidia_pa

	if other_packages:
		installation.add_additional_packages(other_packages)

def install_cachyos_packages(installation):
	print(f"\n{bcolors.GRAY}Installing CachyOS Packages...\n{bcolors.ENDC}")

	if cachy_offline:
		os.system(f"pacstrap {installation.target} {cachyos_packages}")
	else:
		commands = ["pacman --noconfirm -S " + cachyos_packages]
		run_custom_user_commands(commands, installation)

def add_bootloader(installation, bootloader='systemd-bootctl'):
	boot_partition = None
	root_partition = None
	for partition in archinstall.arguments['harddrive']:
		if partition.mountpoint == installation.target + '/boot':
			boot_partition = partition
		elif partition.mountpoint == installation.target:
			root_partition = partition

	with open(f'{installation.target}/boot/loader/entries/cachyos.conf', 'w') as entry:
		entry.write('title CachyOS Linux\n')
		entry.write('linux /vmlinuz-linux-cachyos\n')
		if not is_vm():
			vendor = cpu_vendor()
			if vendor == "AuthenticAMD":
				entry.write("initrd /amd-ucode.img\n")
			elif vendor == "GenuineIntel":
				entry.write("initrd /intel-ucode.img\n")

		entry.write('initrd /initramfs-linux-cachyos.img\n')

		if real_device := installation.detect_encryption(root_partition):
			archinstall.log(f"Identifying root partition by PART-UUID on {real_device}: '{real_device.uuid}'.", level=logging.DEBUG)
			entry.write(f'options cryptdevice=PARTUUID={real_device.uuid}:luksdev root=/dev/mapper/luksdev rw intel_pstate=no_hwp {" ".join(installation.KERNEL_PARAMS)}\n')
		else:
			archinstall.log(f"Identifying root partition by PART-UUID on {root_partition}, looking for '{root_partition.uuid}'.", level=logging.DEBUG)
			entry.write(f'options root=PARTUUID={root_partition.uuid} rw intel_pstate=no_hwp {" ".join(installation.KERNEL_PARAMS)}\n')


def update_bootloader(installation):
	print(f"\n{bcolors.GRAY}Updating the bootloader...\n{bcolors.ENDC}")
	commands = ["pacman --noconfirm -R linux"]
	if archinstall.arguments["bootloader"] == "systemd-bootctl":
		add_bootloader(installation)
	else:
		commands = commands + ["grub-mkconfig -o /boot/grub/grub.cfg"]
	run_custom_user_commands(commands, installation)

def setup_kde_plasma(installation):
	_file = f"/{installation.target}/usr/share/plasma/shells/org.kde.plasma.desktop/contents/layout.js"
	os.system(f"sed -i 's/loadTemplate/\/\/loadTemplate/g' {_file}")

	for user, user_info in archinstall.arguments.get('superusers', {}).items():
		_file = f"/{installation.target}/home/{user}/.config/dolphinrc"
		os.system(f"echo -e \"\n[MainWindow][Toolbar mainToolBar]\nToolButtonStyle=IconOnly\n\" >> {_file}")

def fish_as_default(installation):
	commands = []
	for user, user_info in archinstall.arguments.get('superusers', {}).items():
		commands = commands + [f"usermod --shell $(which fish) {user}"]

	run_custom_user_commands(commands, installation)

def tweak_conf_files(installation):
	paconf = f"/{installation.target}/etc/pacman.conf"
	mkconf = f"/{installation.target}/etc/makepkg.conf"

	os.system(f"sed -i 's/#Color/Color\\n#ILoveCandy/' {paconf}")
	os.system(f"sed -i 's/#ParallelDownloads = 5/ParallelDownloads = 5/' {paconf}")
	os.system(f"sed -i 's/#MAKEFLAGS=\"-j2\"/MAKEFLAGS=\"-j$(expr $(nproc) + 1)\"/' {mkconf}")

def setup_grub_dist_name(installation):
	_file = f"/{installation.target}/etc/default/grub"
	os.system(f"sed -i 's/Arch/CachyOS/g' {_file}")

def run_cachyos_commands(installation):
	print_separator()
	print(f"{bcolors.GRAY}Running CachyOS Setup...\n{bcolors.ENDC}")
	add_cachyos_keyring(installation)
	add_cachyos_repo(installation)
	install_cachyos_packages(installation)

	# grub
	setup_grub_dist_name(installation)

	update_bootloader(installation)

	# other setups
	setup_kde_plasma(installation)
	fish_as_default(installation)
	tweak_conf_files(installation)


def cachy_ask_for_main_filesystem_format():
	options = {
		'xfs': 'xfs',
		'btrfs': 'btrfs',
		'ext4': 'ext4',
		'f2fs': 'f2fs'
	}

	value = archinstall.generic_select(options, "Select which filesystem your main partition should use (by number or name, default is xfs): ", allow_empty_input=True)
	return next((key for key, val in options.items() if val == value), None)

def set_permissions(installation):
	commands = []
	for user, user_info in archinstall.arguments.get('superusers', {}).items():
		commands = commands + [f"chmod +x /home/{user}/.local/bin/set-cachy-theme.sh"]

	run_custom_user_commands(commands, installation)

def ask_user_questions():
	"""
		First, we'll ask the user for a bunch of user input.
		Not until we're satisfied with what we want to install
		will we continue with the actual installation steps.
	"""
	print_separator("1")
	if not archinstall.arguments.get('keyboard-language', None):
		while True:
			try:
				archinstall.arguments['keyboard-language'] = archinstall.select_language(archinstall.list_keyboard_languages()).strip()
				break
			except archinstall.RequirementError as err:
				archinstall.log(err, fg="red")

	# Before continuing, set the preferred keyboard layout/language in the current terminal.
	# This will just help the user with the next following questions.
	if len(archinstall.arguments['keyboard-language']):
		archinstall.set_keyboard_language(archinstall.arguments['keyboard-language'])

	print_separator("2")
	# Set which region to download packages from during the installation
	if not archinstall.arguments.get('mirror-region', None):
		while True:
			try:
				archinstall.arguments['mirror-region'] = archinstall.select_mirror_regions(archinstall.list_mirrors())
				break
			except archinstall.RequirementError as e:
				archinstall.log(e, fg="red")
	else:
		selected_region = archinstall.arguments['mirror-region']
		archinstall.arguments['mirror-region'] = {selected_region: archinstall.list_mirrors()[selected_region]}

	if not archinstall.arguments.get('sys-language', None) and archinstall.arguments.get('advanced', False):
		archinstall.arguments['sys-language'] = input("Enter a valid locale (language) for your OS, (Default: en_US): ").strip()
		archinstall.arguments['sys-encoding'] = input("Enter a valid system default encoding for your OS, (Default: utf-8): ").strip()
		archinstall.log("Keep in mind that if you want multiple locales, post configuration is required.", fg="yellow")

	if not archinstall.arguments.get('sys-language', None):
		archinstall.arguments['sys-language'] = 'en_US'
	if not archinstall.arguments.get('sys-encoding', None):
		archinstall.arguments['sys-encoding'] = 'utf-8'

	print_separator("3")
	# Ask which harddrive/block-device we will install to
	if archinstall.arguments.get('harddrive', None):
		archinstall.arguments['harddrive'] = archinstall.BlockDevice(archinstall.arguments['harddrive'])
	else:
		archinstall.arguments['harddrive'] = archinstall.select_disk(archinstall.all_disks())
		if archinstall.arguments['harddrive'] is None:
			archinstall.arguments['target-mount'] = archinstall.storage.get('MOUNT_POINT', '/mnt')

	# Perform a quick sanity check on the selected harddrive.
	# 1. Check if it has partitions
	# 3. Check that we support the current partitions
	# 2. If so, ask if we should keep them or wipe everything
	if archinstall.arguments['harddrive'] and archinstall.arguments['harddrive'].has_partitions():
		print_separator()
		archinstall.log(f"{archinstall.arguments['harddrive']} contains the following partitions:", fg='yellow')

		# We curate a list pf supported partitions
		# and print those that we don't support.
		partition_mountpoints = {}
		for partition in archinstall.arguments['harddrive']:
			try:
				if partition.filesystem_supported():
					archinstall.log(f" {partition}")
					partition_mountpoints[partition] = None
			except archinstall.UnknownFilesystemFormat as err:
				archinstall.log(f" {partition} (Filesystem not supported)", fg='red')

		# We then ask what to do with the partitions.
		if (option := archinstall.ask_for_disk_layout()) == 'abort':
			archinstall.log("Safely aborting the installation. No changes to the disk or system has been made.")
			exit(1)
		elif option == 'keep-existing':
			archinstall.arguments['harddrive'].keep_partitions = True

			archinstall.log(" ** You will now select which partitions to use by selecting mount points (inside the installation). **")
			archinstall.log(" ** The root would be a simple / and the boot partition /boot (as all paths are relative inside the installation). **")
			mountpoints_set = []
			while True:
				print_separator()
				# Select a partition
				# If we provide keys as options, it's better to convert them to list and sort before passing
				mountpoints_list = sorted(list(partition_mountpoints.keys()))
				partition = archinstall.generic_select(mountpoints_list, "Select a partition by number that you want to set a mount-point for (leave blank when done): ")
				if not partition:
					if set(mountpoints_set) & {'/', '/boot'} == {'/', '/boot'}:
						break

					continue

				# Select a mount-point
				mountpoint = input(f"Enter a mount-point for {partition}: ").strip(' ')
				if len(mountpoint):

					# Get a valid & supported filesystem for the partition:
					while 1:
						new_filesystem = input(f"Enter a valid filesystem for {partition} (leave blank for {partition.filesystem}): ").strip(' ')
						if len(new_filesystem) <= 0:
							if partition.encrypted and partition.filesystem == 'crypto_LUKS':
								old_password = archinstall.arguments.get('!encryption-password', None)
								if not old_password:
									old_password = input(f'Enter the old encryption password for {partition}: ')

								if autodetected_filesystem := partition.detect_inner_filesystem(old_password):
									new_filesystem = autodetected_filesystem
								else:
									archinstall.log("Could not auto-detect the filesystem inside the encrypted volume.", fg='red')
									archinstall.log("A filesystem must be defined for the unlocked encrypted partition.")
									continue
							break

						# Since the potentially new filesystem is new
						# we have to check if we support it. We can do this by formatting /dev/null with the partitions filesystem.
						# There's a nice wrapper for this on the partition object itself that supports a path-override during .format()
						try:
							partition.format(new_filesystem, path='/dev/null', log_formatting=False, allow_formatting=True)
						except archinstall.UnknownFilesystemFormat:
							archinstall.log(f"Selected filesystem is not supported yet. If you want archinstall to support '{new_filesystem}',")
							archinstall.log("please create a issue-ticket suggesting it on github at https://github.com/archlinux/archinstall/issues.")
							archinstall.log("Until then, please enter another supported filesystem.")
							continue
						except archinstall.SysCallError:
							pass  # Expected exception since mkfs.<format> can not format /dev/null. But that means our .format() function supported it.
						break

					# When we've selected all three criteria,
					# We can safely mark the partition for formatting and where to mount it.
					# TODO: allow_formatting might be redundant since target_mountpoint should only be
					#       set if we actually want to format it anyway.
					mountpoints_set.append(mountpoint)
					partition.allow_formatting = True
					partition.target_mountpoint = mountpoint
					# Only overwrite the filesystem definition if we selected one:
					if len(new_filesystem):
						partition.filesystem = new_filesystem

			archinstall.log('Using existing partition table reported above.')
		elif option == 'format-all':
			if not archinstall.arguments.get('filesystem', None):
				print_separator()
				archinstall.arguments['filesystem'] = cachy_ask_for_main_filesystem_format()
				if not archinstall.arguments.get('filesystem', None):
					archinstall.arguments['filesystem'] = "xfs"
			archinstall.arguments['harddrive'].keep_partitions = False
	elif archinstall.arguments['harddrive']:
		# If the drive doesn't have any partitions, safely mark the disk with keep_partitions = False
		# and ask the user for a root filesystem.
		if not archinstall.arguments.get('filesystem', None):
			print_separator()
			archinstall.arguments['filesystem'] = cachy_ask_for_main_filesystem_format()
			if not archinstall.arguments.get('filesystem', None):
				archinstall.arguments['filesystem'] = "xfs"
		archinstall.arguments['harddrive'].keep_partitions = False

	# Get disk encryption password (or skip if blank)
	if archinstall.arguments['harddrive'] and archinstall.arguments.get('!encryption-password', None) is None:
		if passwd := archinstall.get_password(prompt='Enter disk encryption password (leave blank for no encryption): '):
			archinstall.arguments['!encryption-password'] = passwd
			archinstall.arguments['harddrive'].encryption_password = archinstall.arguments['!encryption-password']
	archinstall.arguments["bootloader"] = archinstall.ask_for_bootloader()

	# Get the hostname for the machine
	if not archinstall.arguments.get('hostname', None):
		archinstall.arguments['hostname'] = "CachyOS"

	print_separator("4")
	# Ask for a root password (optional, but triggers requirement for super-user if skipped)
	if not archinstall.arguments.get('!root-password', None):
		archinstall.arguments['!root-password'] = archinstall.get_password(prompt='Enter root password (Recommendation: leave blank to leave root disabled): ')

	# Ask for additional users (super-user if root pw was not set)
	archinstall.arguments['users'] = {}
	archinstall.arguments['superusers'] = {}
	if not archinstall.arguments.get('!root-password', None):
		archinstall.arguments['superusers'] = archinstall.ask_for_superuser_account('Enter a username (required super-user with sudo privileges): ', forced=True)

	else:
		print_separator()
		users, superusers = archinstall.ask_for_additional_users('Enter a username to create a additional user (leave blank to skip & continue): ')
		archinstall.arguments['users'] = users
		archinstall.arguments['superusers'] = {**archinstall.arguments['superusers'], **superusers}

	print_separator("5")
	print("1- minimum installation (no desktop)")
	print("2- minimam KDE plasma desktop")
	print("3- moderated KDE plasma desktop (default, recommended)")
	print("4- full KDE plasma desktop")
	print("5- other options")
	answer = input("Select installation (1, 2, 3, 4, or 5): ")
	desktop_env = False

	if answer == "1":
		archinstall.arguments["installation_selection"] = "minimum"
	elif answer == "2":
		archinstall.arguments["installation_selection"] = "minimam KDE"
		desktop_env = True;
	elif answer == "3":
		archinstall.arguments["installation_selection"] = "moderated KDE"
		desktop_env = True;
	elif answer == "4":
		archinstall.arguments["installation_selection"] = "full KDE"
		desktop_env = True;
	elif answer == "5":
		pass
	else:
		archinstall.arguments["installation_selection"] = "moderated KDE"
		desktop_env = True;

	if not archinstall.arguments.get('installation_selection', None):
		# Ask for archinstall-specific profiles (such as desktop environments etc)
		if not archinstall.arguments.get('profile', None):
			archinstall.arguments['profile'] = archinstall.select_profile()
		else:
			archinstall.arguments['profile'] = Profile(installer=None, path=archinstall.arguments['profile'])

	# Check the potentially selected profiles preparations to get early checks if some additional questions are needed.
	if archinstall.arguments.get('profile', None) and archinstall.arguments['profile'].has_prep_function():
		with archinstall.arguments['profile'].load_instructions(namespace=f"{archinstall.arguments['profile'].namespace}.py") as imported:
			if not imported._prep_function():
				archinstall.log(' * Profile\'s preparation requirements was not fulfilled.', fg='red')
				exit(1)

	# Ask about audio server selection if one is not already set
	if not archinstall.arguments.get('audio', None):
		# only ask for audio server selection on a desktop profile
		if desktop_env or (archinstall.arguments.get('profile', None) and str(archinstall.arguments['profile']) == 'Profile(desktop)'):
			print_separator()
			archinstall.arguments['audio'] = archinstall.ask_for_audio_selection()
		else:
			# packages installed by a profile may depend on audio and something may get installed anyways, not much we can do about that.
			# we will not try to remove packages post-installation to not have audio, as that may cause multiple issues
			archinstall.arguments['audio'] = None

	# Ask for preferred kernel:
	if not archinstall.arguments.get("kernels", None):
		archinstall.arguments['kernels'] = ["linux"]

	print_separator("6")
	# ask for ucode
	# detect cpu
	cpu = ""
	d_cpu = subprocess.check_output("lscpu | grep \"^Vendor\" | uniq | awk '{print $3}'", shell=True)
	d_cpu = d_cpu.decode(sys.stdout.encoding).strip()
	print("CPU vendor detection...")
	if d_cpu == "GenuineIntel":
		cpu = "intel"
	elif d_cpu == "AuthenticAMD":
		cpu = "amd"

	print("Vendor: " + d_cpu)
	if cpu:
		answer = input(f"it seems you are running on an {cpu} machine, install {cpu}-ucode? (Y/n): ")
		if not answer or answer.lower() == "y":
			archinstall.arguments["ucode"] = cpu + "-ucode"

	# Ask or Call the helper function that asks the user to optionally configure a network.
	if not archinstall.arguments.get('nic', None):
		archinstall.arguments['nic'] = {'nic': 'Use NetworkManager to control and manage your internet connection', 'NetworkManager': True}

	# Graphics Drivers
	print_separator("7")
	print("Graphics Drivers:")
	print("1- X.org Intel: i810/i830/i915/945G/G965+ video drivers")
	print("2- Nouveau: Open Source 3D acceleration driver for nVidia cards")
	print("3- X.org AMD: amdgpu video driver")
	print("4- X.org vmware video driver")
	print("5- X.org ati video driver")
	print("6- X.org vesa video driver")
	print("7- X.Org Openchrome drivers")
	print("8- NVIDIA drivers for linux")
	answer = input("Select driver 1, 2, 3, ... 8 (leave blank to skip): ")

	if answer == "1":
		archinstall.arguments["graphics_driver"] = "Xorg Intel"
	elif answer == "2":
		archinstall.arguments["graphics_driver"] = "Nouveau"
	elif answer == "3":
		archinstall.arguments["graphics_driver"] = "Xorg AMD"
	elif answer == "4":
		archinstall.arguments["graphics_driver"] = "Xorg vmware"
	elif answer == "5":
		archinstall.arguments["graphics_driver"] = "Xorg ati"
	elif answer == "6":
		archinstall.arguments["graphics_driver"] = "Xorg vesa"
	elif answer == "7":
		archinstall.arguments["graphics_driver"] = "Xorg Openchrome"
	elif answer == "8":
		archinstall.arguments["graphics_driver"] = "Xorg Nvidia"

	print_separator("8")
	if not archinstall.arguments.get('timezone', None):
		archinstall.arguments['timezone'] = archinstall.ask_for_a_timezone()

	print_separator("9")
	if archinstall.arguments['timezone']:
		if not archinstall.arguments.get('ntp', False):
			archinstall.arguments['ntp'] = input("Would you like to use automatic time synchronization (NTP) with the default time servers? [Y/n]: ").strip().lower() in ('y', 'yes', '')
			if archinstall.arguments['ntp']:
				archinstall.log("Hardware time and other post-configuration steps might be required in order for NTP to work. For more information, please check the Arch wiki.", fg="yellow")

def wipe_disk():
	# umount partitions in case they are mounted before
	for partition in archinstall.arguments['harddrive']:
		print(f"umount {partition.path}")
		os.system(f"umount -l {partition.path}")
		os.system(f"umount -f {partition.path}")

	# wipe entire disk
	_disk = archinstall.arguments['harddrive'].path
	os.system(f"umount -f {_disk}")
	print(f"sfdisk --delete {_disk}")
	os.system("sfdisk --delete " + _disk)

	if has_uefi():
		print("mkfs.vfat " + _disk)
		os.system("mkfs.vfat " + _disk)

	archinstall.arguments['harddrive'].flush_cache()

def perform_installation_steps():
	print()
	print('This is your chosen configuration:')
	archinstall.log("-- Guided template chosen (with below config) --", level=logging.DEBUG)
	user_configuration = json.dumps(archinstall.arguments, indent=4, sort_keys=True, cls=archinstall.JSON)
	with open("/var/log/archinstall/user_configuration.json", "w") as config_file:
		config_file.write(user_configuration)

	os.system("more /var/log/archinstall/user_configuration.json")

	print()

	if not archinstall.arguments.get('silent'):
		input('Press Enter to continue.')

	"""
		Issue a final warning before we continue with something un-revertable.
		We mention the drive one last time, and count from 5 to 0.
	"""

	if archinstall.arguments.get('harddrive', None):
		print(f" ! Formatting {archinstall.arguments['harddrive']} in ")

		"""
			Setup the blockdevice, filesystem (and optionally encryption).
			Once that's done, we'll hand over to perform_installation()
		"""
		mode = archinstall.GPT
		if has_uefi() is False:
			mode = archinstall.MBR

		if archinstall.arguments['harddrive'].keep_partitions is False:
			wipe_disk()

		with archinstall.Filesystem(archinstall.arguments['harddrive'], mode) as fs:
			# Wipe the entire drive if the disk flag `keep_partitions`is False.
			if archinstall.arguments['harddrive'].keep_partitions is False:
				fs.use_entire_disk(root_filesystem_type=archinstall.arguments.get('filesystem', 'xfs'))

			# Check if encryption is desired and mark the root partition as encrypted.
			if archinstall.arguments.get('!encryption-password', None):
				root_partition = fs.find_partition('/')
				root_partition.encrypted = True

			# After the disk is ready, iterate the partitions and check
			# which ones are safe to format, and format those.
			for partition in archinstall.arguments['harddrive']:
				if partition.safe_to_format():
					# Partition might be marked as encrypted due to the filesystem type crypt_LUKS
					# But we might have omitted the encryption password question to skip encryption.
					# In which case partition.encrypted will be true, but passwd will be false.
					if partition.encrypted and (passwd := archinstall.arguments.get('!encryption-password', None)):
						partition.encrypt(password=passwd)
					else:
						partition.format()
				else:
					archinstall.log(f"Did not format {partition} because .safe_to_format() returned False or .allow_formatting was False.", level=logging.DEBUG)

			if archinstall.arguments.get('!encryption-password', None):
				# First encrypt and unlock, then format the desired partition inside the encrypted part.
				# archinstall.luks2() encrypts the partition when entering the with context manager, and
				# unlocks the drive so that it can be used as a normal block-device within archinstall.
				with archinstall.luks2(fs.find_partition('/'), 'luksloop', archinstall.arguments.get('!encryption-password', None)) as unlocked_device:
					unlocked_device.format(fs.find_partition('/').filesystem)
					unlocked_device.mount(archinstall.storage.get('MOUNT_POINT', '/mnt'))
			else:
				fs.find_partition('/').mount(archinstall.storage.get('MOUNT_POINT', '/mnt'))

			if has_uefi():
				fs.find_partition('/boot').mount(archinstall.storage.get('MOUNT_POINT', '/mnt') + '/boot')

	perform_installation(archinstall.storage.get('MOUNT_POINT', '/mnt'))


def perform_installation(mountpoint):
	"""
	Performs the installation steps on a block device.
	Only requirement is that the block devices are
	formatted and setup prior to entering this function.
	"""
	with archinstall.Installer(mountpoint, kernels=archinstall.arguments.get('kernels', 'linux')) as installation:
		# if len(mirrors):
		# Certain services might be running that affects the system during installation.
		# Currently, only one such service is "reflector.service" which updates /etc/pacman.d/mirrorlist
		# We need to wait for it before we continue since we opted in to use a custom mirror/region.
		installation.log('Waiting for automatic mirror selection (reflector) to complete.', level=logging.INFO)
		while archinstall.service_state('reflector') not in ('dead', 'failed'):
			time.sleep(1)
		# Set mirrors used by pacstrap (outside of installation)
		if archinstall.arguments.get('mirror-region', None):
			archinstall.use_mirrors(archinstall.arguments['mirror-region'])  # Set the mirrors for the live medium
		if installation.minimal_installation():
			installation.set_locale(archinstall.arguments['sys-language'], archinstall.arguments['sys-encoding'].upper())
			installation.set_hostname(archinstall.arguments['hostname'])
			if archinstall.arguments['mirror-region'].get("mirrors", None) is not None:
				installation.set_mirrors(archinstall.arguments['mirror-region'])  # Set the mirrors in the installation medium
			if archinstall.arguments["bootloader"] == "grub-install" and has_uefi():
				installation.add_additional_packages("grub")
			installation.add_bootloader(archinstall.arguments["bootloader"])

			# If user selected to copy the current ISO network configuration
			# Perform a copy of the config
			if archinstall.arguments.get('nic', {}) == 'Copy ISO network configuration to installation':
				installation.copy_iso_network_config(enable_services=True)  # Sources the ISO network configuration to the install medium.
			elif archinstall.arguments.get('nic', {}).get('NetworkManager', False):
				installation.add_additional_packages("networkmanager")
				installation.enable_service('NetworkManager.service')
			# Otherwise, if a interface was selected, configure that interface
			elif archinstall.arguments.get('nic', {}):
				installation.configure_nic(**archinstall.arguments.get('nic', {}))
				installation.enable_service('systemd-networkd')
				installation.enable_service('systemd-resolved')

			if archinstall.arguments.get('audio', None) is not None:
				installation.log(f"This audio server will be used: {archinstall.arguments.get('audio', None)}", level=logging.INFO)
				if archinstall.arguments.get('audio', None) == 'pipewire':
					print('Installing pipewire ...')

					installation.add_additional_packages(["pipewire", "pipewire-alsa", "pipewire-jack", "pipewire-media-session", "pipewire-pulse", "gst-plugin-pipewire", "libpulse"])
				elif archinstall.arguments.get('audio', None) == 'pulseaudio':
					print('Installing pulseaudio ...')
					installation.add_additional_packages("pulseaudio")
			else:
				installation.log("No audio server will be installed.", level=logging.INFO)

			if archinstall.arguments.get('packages', None) and archinstall.arguments.get('packages', None)[0] != '':
				installation.add_additional_packages(archinstall.arguments.get('packages', None))

			if archinstall.arguments.get('profile', None):
				installation.install_profile(archinstall.arguments.get('profile', None))

			# copy /etc/skel before creating users
			os.system(f"cp -rT /etc/skel {installation.target}/etc/skel")

			for user, user_info in archinstall.arguments.get('users', {}).items():
				installation.user_create(user, user_info["!password"], sudo=False)

			for superuser, user_info in archinstall.arguments.get('superusers', {}).items():
				installation.user_create(superuser, user_info["!password"], sudo=True)

			if timezone := archinstall.arguments.get('timezone', None):
				installation.set_timezone(timezone)

			if archinstall.arguments.get('ntp', False):
				installation.activate_ntp()

			if (root_pw := archinstall.arguments.get('!root-password', None)) and len(root_pw):
				installation.user_set_pw('root', root_pw)

			# This step must be after profile installs to allow profiles to install language pre-requisits.
			# After which, this step will set the language both for console and x11 if x11 was installed for instance.
			installation.set_keyboard_language(archinstall.arguments['keyboard-language'])

			if archinstall.arguments.get('profile', None) and archinstall.arguments['profile'].has_post_install():
				with archinstall.arguments['profile'].load_instructions(namespace=f"{archinstall.arguments['profile'].namespace}.py") as imported:
					if not imported._post_install():
						archinstall.log(' * Profile\'s post configuration requirements was not fulfilled.', fg='red')
						exit(1)

		# install kde if selected
		install_selected_packages(installation)

		# copy /etc/sddm.conf.d (maybe not needed when added to airootfs)
		os.system(f"mkdir {installation.target}/etc/sddm.conf.d/")
		os.system(f"touch {installation.target}/etc/sddm.conf")
		os.system(f"cp /etc/sddm.conf.d/kde_settings.conf {installation.target}/etc/sddm.conf.d/")

		# fixing files/folders permissions
		set_permissions(installation)

		# enable some services if kde is isntalled
		enable_services(installation)

		# If the user provided a list of services to be enabled, pass the list to the enable_service function.
		# Note that while it's called enable_service, it can actually take a list of services and iterate it.
		if archinstall.arguments.get('services', None):
			installation.enable_service(*archinstall.arguments['services'])

		# If the user provided custom commands to be run post-installation, execute them now.
		if archinstall.arguments.get('custom-commands', None):
			run_custom_user_commands(archinstall.arguments['custom-commands'], installation)

		# Add cachyos keyring and install cachy packages
		run_cachyos_commands(installation)

	# For support reasons, we'll log the disk layout post installation (crash or no crash)
	archinstall.log(f"Disk states after installing: {archinstall.disk_layouts()}", level=logging.DEBUG)


print(bcolors.GRAY + "Check if Arch Linux mirrors are not reachable... " + bcolors.ENDC, flush=True, end="")
if not check_mirror_reachable():
	log_file = os.path.join(archinstall.storage.get('LOG_PATH', None), archinstall.storage.get('LOG_FILE', None))
	archinstall.log(f"Arch Linux mirrors are not reachable. Please check your internet connection and the log file '{log_file}'.", level=logging.INFO, fg="red")
	exit(1)
print(bcolors.OKGREEN + "(OK)" + bcolors.ENDC)

if archinstall.arguments.get('silent', None) is None:
	ask_user_questions()

perform_installation_steps()

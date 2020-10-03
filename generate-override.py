import subprocess
import re
from pathlib import Path
from collections import namedtuple

Display = namedtuple('Display', ['vendor_id', 'product_id', 'name', 'edid'])


def get_ioreg_displays():
    """
    Query 'ioreg' for displays, and return the output as a string
    """
    cmd = ['ioreg', '-l', '-d0', '-w', '0', '-r', '-c', 'AppleDisplay']
    return subprocess.run(cmd, text=True, capture_output=True).stdout


def find_display_data(ioreg):
    """
    Finds (vendorid, productid, edid) tuples for displays in the ioreg data
    """
    edids = re.findall("IODisplayEDID.*?<([a-z0-9]+)>", ioreg)
    vendorids = re.findall("DisplayVendorID.*?([0-9]+)", ioreg)
    productids = re.findall("DisplayProductID.*?([0-9]+)", ioreg)
    return [Display(
        vendor_id = v,
        product_id = p,
        name = display_name_from_edid(e),
        edid = e
    ) for v, p, e in zip(vendorids, productids, edids)]


def display_name_from_edid(edid):
    """
    Extract the name of the display from the EDID data

    The monitor name is stored in the 13 bytes of text following "000000fc00".
    If the name is shorter, it is terminated with a newline (0a) and then
    padded with spaces.

    See https://en.wikipedia.org/wiki/Extended_Display_Identification_Data
    """
    display_name_descriptor = '000000fc00'
    if not display_name_descriptor in edid:
        return 'Display'

    from_index = edid.index(display_name_descriptor) + 10
    to_index = from_index + 26

    name_hex = edid[from_index:to_index]
    name = bytearray.fromhex(name_hex).decode().rstrip()

    return name


def generate_override_file(display):
    """
    Generates an override file for the display
    """
    vendorpath = "DisplayVendorID-%0.2x" % int(display.vendor_id)
    productpath = "DisplayProductId-%0.2x" % int(display.product_id)
    path = Path('.') / 'Overrides' / vendorpath / productpath

    if path.exists():
        print('File already exists, nothing to do', path)
        return path

    print('Generating file', path)
    path.parent.mkdir(parents=True, exist_ok=True)

    path.touch()
    path.write_text(f"""\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>DisplayProductName</key>
	<string>{display.name} (EDID override)</string>
	<key>edid-patches</key>
	<array>
		<dict>
			<key>offset</key>
			<integer>131</integer>
			<key>data</key>
			<data>wQ==</data>
		</dict>
	</array>
</dict>
</plist>""")

    return path


def print_install_command(display, path):
    """
    Print out the command to install the override
    """
    print(f"Install the override for {display.name} with the following command:")

    overrides = Path('/Library/Displays/Contents/Resources')
    source = path.absolute()
    target = overrides / path
    directory = target.parent

    print(f"sudo mkdir -p {directory} && sudo cp {source} {target}")


def main():
    ioreg = get_ioreg_displays()
    displays = find_display_data(ioreg)
    for display in displays:
        path = generate_override_file(display)
        print_install_command(display, path)


if __name__ == "__main__":
    main()

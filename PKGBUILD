# Maintainer: Hamad Al Marri <hamad@cachyos.org>

pkgname=cachyos-installer
pkgver=1
pkgrel=1
pkgdesc="The installer script for CachyOS"
arch=(x86_64)
options=('!strip')

depends=('figlet')

source=("cachyos_install.py" "install_cachyos")
sha512sums=('SKIP' 'SKIP')

package() {
	install -dm 755 $pkgdir/usr/lib/python3.9/site-packages/archinstall/examples/
	install -dm 755 $pkgdir/usr/local/bin/

	cp ./cachyos_install.py ${pkgdir}/usr/lib/python3.9/site-packages/archinstall/examples/
	cp ./install_cachyos ${pkgdir}/usr/local/bin
}


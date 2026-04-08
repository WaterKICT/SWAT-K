# -*- coding: utf-8 -*-
def classFactory(iface):
    """Load SwatKPlugin class from file plugin.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    from .plugin import SwatKPlugin
    return SwatKPlugin(iface)

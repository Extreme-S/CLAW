"""macOS: 让窗口浮于全屏应用之上。仅在 macOS 生效，其他平台静默跳过。"""

import sys

def elevate_window(widget):
    """将 QWidget 提升到 macOS 最高窗口层级（全屏之上）。"""
    if sys.platform != "darwin":
        return
    try:
        import ctypes
        import ctypes.util

        objc = ctypes.cdll.LoadLibrary(ctypes.util.find_library("objc"))

        objc.objc_getClass.restype = ctypes.c_void_p
        objc.sel_registerName.restype = ctypes.c_void_p
        objc.objc_msgSend.restype = ctypes.c_void_p
        objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p]

        # NSView* -> [view window] -> NSWindow*
        view_ptr = int(widget.winId())
        ns_window = objc.objc_msgSend(view_ptr, objc.sel_registerName(b"window"))
        if not ns_window:
            return

        # [nsWindow setLevel: 1000]  (NSScreenSaverWindowLevel — 高于全屏)
        objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_long]
        objc.objc_msgSend(ns_window, objc.sel_registerName(b"setLevel:"), 1000)

        # [nsWindow setCollectionBehavior: canJoinAllSpaces | fullScreenAuxiliary]
        NSWindowCollectionBehaviorCanJoinAllSpaces = 1 << 0
        NSWindowCollectionBehaviorFullScreenAuxiliary = 1 << 8
        behavior = NSWindowCollectionBehaviorCanJoinAllSpaces | NSWindowCollectionBehaviorFullScreenAuxiliary
        objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong]
        objc.objc_msgSend(ns_window, objc.sel_registerName(b"setCollectionBehavior:"), behavior)

        # 恢复默认 argtypes
        objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    except Exception:
        pass

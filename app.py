# -*- coding: utf-8 -*-
"""Gaia DR3 資料擷取工具 — 打包版進入點（PyInstaller onefile）
雙擊 exe 後：啟動本機伺服器 → 自動開啟瀏覽器 → 保留視窗顯示狀態。
關閉視窗即結束工具。
"""
import sys
import time
import threading
import webbrowser

import server

URL = f"http://localhost:{server.PORT}"

BANNER = f"""
============================================================
   Gaia DR3 資料擷取工具
============================================================

  瀏覽器將自動開啟：{URL}

  ▸ 若瀏覽器沒有自動跳出，請手動在網址列輸入上面那行網址。
  ▸ 使用完畢後，直接關閉這個黑色視窗即可結束工具。
  ▸ 這個視窗會保持開啟，代表工具正在執行中，屬於正常現象。

============================================================
"""


def open_browser_later():
    time.sleep(1.5)
    webbrowser.open(URL)


def main():
    print(BANNER)
    try:
        srv = server.Server(("127.0.0.1", server.PORT), server.Handler)
    except OSError:
        # 埠已被占用 = 工具已在執行，直接開瀏覽器即可
        print("  偵測到工具已在執行中，正在開啟瀏覽器…\n")
        webbrowser.open(URL)
        time.sleep(3)
        return

    threading.Thread(target=open_browser_later, daemon=True).start()
    print("  伺服器已啟動，請稍候瀏覽器開啟…（按 Ctrl+C 或關閉視窗可結束）\n")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n  工具已結束，感謝使用。")


if __name__ == "__main__":
    main()

import sys
import webview

def main():
    if len(sys.argv) < 2:
        print('Usage: open_webview.py <url>')
        return
    url = sys.argv[1]
    # Create a simple webview window showing the URL
    webview.create_window('記事表示', url)
    webview.start()

if __name__ == '__main__':
    main()

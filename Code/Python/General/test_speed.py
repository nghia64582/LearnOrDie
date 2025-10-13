import speedtest as st
def speed_test():
    s = st.Speedtest()
    s.get_best_server()
    download_speed = s.download() / 1_000_000  # Convert to Mbps
    upload_speed = s.upload() / 1_000_000      # Convert to Mbps
    return download_speed, upload_speed

if __name__ == "__main__":
    download, upload = speed_test()
    print(f"Download Speed: {download:.2f} Mbps")
    print(f"Upload Speed: {upload:.2f} Mbps")
import requests
import concurrent.futures

# Example proxy list URL: https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt

# Function to check a single proxy
def check_proxy(proxy, timeout):
    try:
        proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
        response = requests.get("http://httpbin.org/ip", proxies=proxies, timeout=timeout)
        if response.status_code == 200:
            print(f"[Working] {proxy}")
            return proxy
    except:
        print(f"[Not working] {proxy}")
        return None

# Main function
def main():
    # Prompt for the proxy list URL
    proxy_list_url = input("Do you have a proxy list URL? Please insert it(Example proxy list URL: https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt): ")  # Example: https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt
    
    # Load the proxy list
    try:
        response = requests.get(proxy_list_url)
        response.raise_for_status()
        proxies = response.text.splitlines()
        total_proxies = len(proxies)
        print(f"Loaded {total_proxies} proxies for checking.")
    except Exception as e:
        print("Failed to load the proxy list:", e)
        return

    # Prompt for the number of proxies to check
    while True:
        try:
            check_count = int(input(f"How many proxies to check (0 - all, insert from 1 - {total_proxies})? "))
            if 0 <= check_count <= total_proxies:
                break
            else:
                print(f"Please enter a number between 0 and {total_proxies}.")
        except ValueError:
            print("Invalid input. Please enter a number between 0 and {total_proxies}.")

    # Prompt for timeout
    while True:
        try:
            timeout = int(input("Enter timeout in seconds (1 for fast, 5 for slow): "))
            if 1 <= timeout <= 5:
                break
            else:
                print("Please enter a number between 1 and 5.")
        except ValueError:
            print("Invalid input. Please enter a number between 1 and 5.")
    
    # Determine which proxies to check
    if check_count == 0:
        proxies_to_check = proxies
    else:
        proxies_to_check = proxies[:check_count]

    # Logging actions
    print("Starting proxy check...")
    
    # Check proxies in multithreading mode
    working_proxies = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(lambda proxy: check_proxy(proxy, timeout), proxies_to_check))
    
    # Filter working proxies
    working_proxies = [proxy for proxy in results if proxy]

    # Attempt to write working proxies to a file
    try:
        with open("working_proxies.txt", "w") as file:
            for proxy in working_proxies:
                file.write(proxy + "\n")
        print("Working proxies have been written to 'working_proxies.txt'.")
    except Exception as e:
        print("Failed to write to file:", e)
    
    # Final report
    print(f"Check completed.")
    print(f"Working proxies: {len(working_proxies)}")
    print(f"Not working proxies: {len(proxies_to_check) - len(working_proxies)}")
    
if __name__ == "__main__":
    main()

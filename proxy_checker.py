import requests
import concurrent.futures
import sys

# Example proxy list URL: https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt

# Function to check a single proxy
def check_proxy(proxy, timeout, proxy_type):
    try:
        proxies = {proxy_type: f"{proxy_type}://{proxy}"}
        response = requests.get("http://httpbin.org/ip", proxies=proxies, timeout=timeout)
        if response.status_code == 200:
            print(f"[Working] {proxy} ({proxy_type})")
            return proxy
    except:
        print(f"[Not working] {proxy} ({proxy_type})")
        return None

# Main function
def main():
    # Prompt for the proxy type
    print("Select the type of proxy to check:")
    print("1. HTTP")
    print("2. SOCKS4")
    print("3. SOCKS5")
    
    while True:
        try:
            proxy_type_choice = int(input("Enter your choice (1-3): "))
            if proxy_type_choice in [1, 2, 3]:
                break
            else:
                print("Please enter a valid number (1-3).")
        except ValueError:
            print("Invalid input. Please enter a number (1-3).")

    proxy_types = {1: 'http', 2: 'socks4', 3: 'socks5'}
    selected_proxy_type = proxy_types[proxy_type_choice]

    # Prompt for the proxy list URL
    proxy_list_url = input("Do you have a proxy list URL? (Example proxy list URL: https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt) Please insert it: ")  # Example: https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt
    
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
            check_count = int(input(f"How many proxies to check (0 - all, 1 - {total_proxies})? "))
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

    # Initialize lists for working proxies
    working_proxies_http = []
    working_proxies_socks4 = []
    working_proxies_socks5 = []

    # Check proxies in multithreading mode for each type
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # Check HTTP proxies if selected
        if selected_proxy_type == 'http':
            results_http = list(executor.map(lambda proxy: check_proxy(proxy, timeout, 'http'), proxies_to_check))
            working_proxies_http = [proxy for proxy in results_http if proxy]

        # Check SOCKS4 proxies if selected
        elif selected_proxy_type == 'socks4':
            results_socks4 = list(executor.map(lambda proxy: check_proxy(proxy, timeout, 'socks4'), proxies_to_check))
            working_proxies_socks4 = [proxy for proxy in results_socks4 if proxy]

        # Check SOCKS5 proxies if selected
        elif selected_proxy_type == 'socks5':
            results_socks5 = list(executor.map(lambda proxy: check_proxy(proxy, timeout, 'socks5'), proxies_to_check))
            working_proxies_socks5 = [proxy for proxy in results_socks5 if proxy]

    # Attempt to write working proxies to the corresponding file
    try:
        if selected_proxy_type == 'http':
            with open("working_http_proxies.txt", "w") as file:
                for proxy in working_proxies_http:
                    file.write(proxy + "\n")
            print("Working HTTP proxies have been written to 'working_http_proxies.txt'.")
        
        elif selected_proxy_type == 'socks4':
            with open("working_socks4_proxies.txt", "w") as file:
                for proxy in working_proxies_socks4:
                    file.write(proxy + "\n")
            print("Working SOCKS4 proxies have been written to 'working_socks4_proxies.txt'.")
        
        elif selected_proxy_type == 'socks5':
            with open("working_socks5_proxies.txt", "w") as file:
                for proxy in working_proxies_socks5:
                    file.write(proxy + "\n")
            print("Working SOCKS5 proxies have been written to 'working_socks5_proxies.txt'.")
        
    except Exception as e:
        print("Failed to write to file:", e)
    
    # Final report
    print(f"\nCheck completed.")
    if selected_proxy_type == 'http':
        print(f"Working HTTP proxies: {len(working_proxies_http)}")
    elif selected_proxy_type == 'socks4':
        print(f"Working SOCKS4 proxies: {len(working_proxies_socks4)}")
    elif selected_proxy_type == 'socks5':
        print(f"Working SOCKS5 proxies: {len(working_proxies_socks5)}")

    print(f"Total proxies checked: {len(proxies_to_check)}")
    
    # Wait for user input before exiting
    input("\nPress any key to exit...")

if __name__ == "__main__":
    main()

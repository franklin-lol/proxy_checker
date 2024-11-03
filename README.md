# Proxy Checker
A simple and efficient proxy checker written in Python that allows users to verify the availability of HTTP proxies. This tool downloads a list of proxies from a specified URL, checks their functionality, and logs the working proxies into a text file for later use.

Features
Proxy List Input: Enter a URL to download a list of proxies.
Check Proxy Count: Specify how many proxies to check (0 for all, or a specific number).
Timeout Configuration: Set the timeout duration for each proxy check (between 1 and 5 seconds).
Real-time Status Updates: Displays the status of each proxy (working or not) during the check.
Output Logging: Saves all working proxies into a text file named working_proxies.txt.
Requirements
Python 3.11
requests library
Usage
Clone the repository.
Install the required dependencies.
Run the script and follow the prompts to input the proxy URL, number of proxies to check, and timeout duration.
![image](https://github.com/user-attachments/assets/842b4e75-bdb7-44e0-8e00-48a8e22eaa0f)

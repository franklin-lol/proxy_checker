import requests
import concurrent.futures

# Функция для проверки одного прокси
def check_proxy(proxy, timeout):
    try:
        proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
        response = requests.get("http://httpbin.org/ip", proxies=proxies, timeout=timeout)
        if response.status_code == 200:
            print(f"[Рабочий] {proxy}")
            return proxy
    except:
        print(f"[Не работает] {proxy}")
        return None

# Основная функция
def main():
    # Запрос ссылки на список прокси
    proxy_list_url = input("У вас есть ссылка для прокси? Вставьте её: ")
    
    # Загрузка списка прокси
    try:
        response = requests.get(proxy_list_url)
        response.raise_for_status()
        proxies = response.text.splitlines()
        total_proxies = len(proxies)
        print(f"Загружено {total_proxies} прокси для проверки.")
    except Exception as e:
        print("Не удалось загрузить список прокси:", e)
        return

    # Запрос количества прокси для проверки
    while True:
        try:
            check_count = int(input(f"Сколько прокси проверить (0 - все, или от 1 - {total_proxies})? "))
            if 0 <= check_count <= total_proxies:
                break
            else:
                print(f"Пожалуйста, введите число от 0 до {total_proxies}.")
        except ValueError:
            print("Неверный ввод. Введите число от 0 до {total_proxies}.")

    # Запрос времени ожидания
    while True:
        try:
            timeout = int(input("Введите время ожидания от 1 до 5 секунд (например, 1 — быстро, 5 — медленно): "))
            if 1 <= timeout <= 5:
                break
            else:
                print("Пожалуйста, введите число от 1 до 5.")
        except ValueError:
            print("Неверный ввод. Введите число от 1 до 5.")
    
    # Определяем прокси для проверки
    if check_count == 0:
        proxies_to_check = proxies
    else:
        proxies_to_check = proxies[:check_count]

    # Логирование действий
    print("Начинаю проверку прокси...")
    
    # Проверка прокси в многопоточном режиме
    working_proxies = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(lambda proxy: check_proxy(proxy, timeout), proxies_to_check))
    
    # Фильтрация рабочих прокси
    working_proxies = [proxy for proxy in results if proxy]

    # Проверка, существует ли файл и создание его, если нет
    try:
        with open("working_proxies.txt", "w") as file:
            for proxy in working_proxies:
                file.write(proxy + "\n")
        print("Рабочие прокси записаны в файл 'working_proxies.txt'.")
    except Exception as e:
        print("Не удалось записать в файл:", e)
    
    # Итоговый отчет
    print(f"Проверка завершена.")
    print(f"Рабочих прокси: {len(working_proxies)}")
    print(f"Нерабочих прокси: {len(proxies_to_check) - len(working_proxies)}")
    
if __name__ == "__main__":
    main()

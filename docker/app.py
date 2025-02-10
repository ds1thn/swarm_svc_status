import docker
from tabulate import tabulate
from datetime import datetime
from colorama import Fore, Style, init

# Инициализация Docker клиента и colorama
client = docker.from_env()
init(autoreset=True)

# Список исключений (сервисы, которые не нужно включать в таблицу)
exclude_services = ["service1", "service2"]

# Маппинг сервисов на группы
service_groups = {
    'dbs': ['clickhouse', 'mongo', 'postgresql', 'minio'],
    'nosql': ['redis', 'scylla'],
    'cache': ['kafka', 'mq'],
    'mon': ['alertmanager', 'prometheus', 'blackbox', 'grafana', 'filebeat', 'docker-events-slack', 'cron-docker-rollback'],
    'tech': ['busybox_app', 'openvpn', 'wg', 'named', 'gitlab-runner', 'bind', 'homelab'],
}

services = client.services.list()
grouped_data = {group: [] for group in service_groups}
grouped_data['other'] = []

current_time = datetime.utcnow()
network_name = "octo"

def get_task_ips(task, network_name):
    ips = []
    if task['Status']['State'] == 'running':
        networks = task['NetworksAttachments']
        for network in networks:
            if network['Network']['Spec']['Name'] == network_name:
                ips.append(network['Addresses'][0].split('/')[0])
    return ips

def format_ips(ip_list, max_per_line=3):
    grouped_ips = [", ".join(ip_list[i:i + max_per_line]) for i in range(0, len(ip_list), max_per_line)]
    return "\n".join(grouped_ips)

for service in services:
    service_name = service.name
    if service_name in exclude_services:
        continue

    service_info = service.attrs
    task_template = service_info['Spec']['TaskTemplate']
    resources = task_template.get('Resources', {})
    limits = resources.get('Limits', {})
    
    memory_limit = limits.get('MemoryBytes', 'нет')
    cpu_limit = limits.get('NanoCPUs', 'нет')
    
    if memory_limit != 'нет':
        memory_limit = f"{memory_limit / (1024**3):.2f}g"
    if cpu_limit != 'нет':
        cpu_limit = f"{cpu_limit / (10**9):.2f}"

    container_spec = task_template.get('ContainerSpec', {})
    healthcheck = container_spec.get('Healthcheck', {})
    healthcheck_status = 'нет'
    if healthcheck:
        healthcheck_status = "настроен"

    mode = service_info['Spec']['Mode']
    replicas = mode.get('Replicated', {}).get('Replicas', 'нет')

    last_update = service_info['UpdatedAt']
    # last_update_truncated = last_update[:26] + 'Z'
    # last_update_dt = datetime.fromisoformat(last_update_truncated[:-1])
    # time_difference = current_time - last_update_dt
    # days = time_difference.days
    # hours, remainder = divmod(time_difference.seconds, 3600)
    # minutes, _ = divmod(remainder, 60)
    # last_update_formatted = f"{days} дн. {hours} ч. {minutes} мин."

    # Добавляем цвет, если прошло менее 24 часов
    # if days < 1:
    #     last_update_formatted = f"{Fore.GREEN}{last_update_formatted}{Style.RESET_ALL}"
    # else:
    #     last_update_formatted = f"{Fore.RED}{last_update_formatted}{Style.RESET_ALL}"

    service_type = 'other'
    for group, patterns in service_groups.items():
        if any(service_name.startswith(pattern) for pattern in patterns):
            service_type = group
            break

    task_ips = []
    for task in service.tasks():
        task_ips.extend(get_task_ips(task, network_name))

    formatted_ips = format_ips(task_ips) if task_ips else 'нет'

    grouped_data[service_type].append([
        service_name, 
        cpu_limit, 
        memory_limit, 
        healthcheck_status, 
        replicas, 
        # last_update_formatted,
        formatted_ips
    ])

headers = ["Приложение", "CPU", "Memory", "Healthcheck", "Реплики", "Время с последнего обновления", "IP"]

for group, data in grouped_data.items():
    if data:
        sorted_data = sorted(data, key=lambda x: x[0])
        print(f"\nГруппа: {group}")
        print(tabulate(sorted_data, headers, tablefmt="grid"))

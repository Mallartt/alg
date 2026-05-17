import matplotlib.pyplot as plt

def parse_logcat_file(filename):
    times = []
    pitches = []
    nods =[]
    start_time = None
    
    with open(filename, 'r', encoding='utf-8') as file:
        for line in file:
            # Ищем строки, содержащие наш маркер логов Android (буква D и два пробела)
            if ' D  ' in line:
                try:
                    # Вырезаем только полезные данные после " D  "
                    payload = line.split(' D  ')[1].strip()
                    t_str, p_str, n_str = payload.split(';')
                    
                    t = float(t_str)
                    if start_time is None:
                        start_time = t
                    
                    # Переводим время в секунды от начала эксперимента
                    times.append((t - start_time) / 1000.0)
                    pitches.append(float(p_str))
                    nods.append(int(n_str))
                except Exception as e:
                    continue
                    
    return times, pitches, nods

# Читаем данные из загруженных файлов
t_norm, p_norm, n_norm = parse_logcat_file('normal.txt')
t_sleep, p_sleep, n_sleep = parse_logcat_file('sleep.txt')

# Настройка красивого стиля для отчета
plt.style.use('seaborn-v0_8-whitegrid')
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

# График 1: Бодрствование
ax1.plot(t_norm, p_norm, color='#2ca02c', linewidth=2, label='Угол (Pitch)')
ax1.axhline(-15, color='red', linestyle='--', linewidth=1.5, label='Порог засыпания (-15°)')
ax1.set_title('Состояние: Бодрствование (Нормальное вождение)', fontsize=14)
ax1.set_xlabel('Время (секунды)', fontsize=12)
ax1.set_ylabel('Угол наклона головы (градусы)', fontsize=12)
ax1.set_ylim(-130, 130)
ax1.legend()

# График 2: Засыпание
ax2.plot(t_sleep, p_sleep, color='#1f77b4', linewidth=2, label='Угол (Pitch)')
ax2.axhline(-15, color='red', linestyle='--', linewidth=1.5, label='Порог засыпания (-15°)')

# Отмечаем точки кивков (где счетчик увеличивался)
for i in range(1, len(n_sleep)):
    if n_sleep[i] > n_sleep[i-1]:
        ax2.plot(t_sleep[i], p_sleep[i], marker='o', markersize=8, color='red')
        ax2.annotate(f'Кивок {n_sleep[i]}', (t_sleep[i], p_sleep[i]-15), color='red', fontsize=10, ha='center')

ax2.set_title('Состояние: Засыпание (Микросны)', fontsize=14)
ax2.set_xlabel('Время (секунды)', fontsize=12)
ax2.set_ylim(-130, 130)
ax2.legend()

plt.suptitle('Частотно-временные характеристики кивания головой (Pitch)', fontsize=16, y=1.05)
plt.tight_layout()

# Сохраняем картинку в высоком качестве
plt.savefig('sleep_analysis_plot.png', dpi=300, bbox_inches='tight')
plt.show()
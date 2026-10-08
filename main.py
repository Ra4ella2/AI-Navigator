import sqlite3
import ollama

# distance, time, traffic, difficulty
graph = {
    "A": {"B": (4, 6, 2, 1), "C": (2, 4, 1, 1)},
    "B": {"A": (4, 6, 2, 1), "C": (5, 8, 3, 2), "D": (10, 14, 3, 2)},
    "C": {"A": (2, 4, 1, 1), "B": (5, 8, 3, 2), "E": (3, 5, 2, 1)},
    "D": {"B": (10, 14, 3, 2), "E": (4, 6, 2, 2), "F": (11, 15, 4, 3)},
    "E": {"C": (3, 5, 2, 1), "D": (4, 6, 2, 2), "G": (8, 11, 3, 2)},
    "F": {"D": (11, 15, 4, 3), "G": (6, 8, 2, 1)},
    "G": {"E": (8, 11, 3, 2), "F": (6, 8, 2, 1)}
}


# ---------------- DATABASE ----------------

db = sqlite3.connect("navigator.db")
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS routes(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start TEXT,
    finish TEXT,
    route TEXT,
    distance REAL,
    expected_time REAL,
    traffic REAL,
    actual_time REAL,
    actual_distance REAL
)
""")

db.commit()


# ---------------- DIJKSTRA ----------------

def dijkstra(start, finish):
    dist = {v: float("inf") for v in graph}
    prev = {}
    used = set()

    dist[start] = 0

    while True:
        current = None

        for v in graph:
            if v not in used and (current is None or dist[v] < dist[current]):
                current = v

        if current is None or current == finish:
            break

        used.add(current)

        for neighbor, road in graph[current].items():
            new_dist = dist[current] + road[0]

            if new_dist < dist[neighbor]:
                dist[neighbor] = new_dist
                prev[neighbor] = current

    if dist[finish] == float("inf"):
        return None

    route = [finish]

    while route[-1] != start:
        route.append(prev[route[-1]])

    route.reverse()

    return route


# ---------------- ALL ROUTES ----------------
# Простая DFS для поиска альтернатив

def find_all_routes(start, finish, route=None):
    if route is None:
        route = [start]

    if start == finish:
        return [route]

    routes = []

    for neighbor in graph[start]:
        if neighbor not in route:
            routes += find_all_routes(
                neighbor,
                finish,
                route + [neighbor]
            )

    return routes


# ---------------- ROUTE INFO ----------------

def route_info(route):
    distance = 0
    time = 0
    traffic = 0

    for i in range(len(route) - 1):
        road = graph[route[i]][route[i + 1]]

        distance += road[0]
        time += road[1]
        traffic += road[2]

    traffic /= len(route) - 1

    return distance, time, traffic


# ---------------- FIND ROUTE ----------------

def find_route():
    start = input("Початкова точка: ").upper()
    finish = input("Кінцева точка: ").upper()

    if start not in graph or finish not in graph:
        print("Невірна точка.")
        return

    best = dijkstra(start, finish)

    print("\nDijkstra:")
    print(" -> ".join(best))

    # Находим все возможные маршруты
    routes = find_all_routes(start, finish)

    # Сортируем по расстоянию
    routes.sort(key=lambda r: route_info(r)[0])

    # Оставляем только первые 3
    routes = routes[:3]

    print("\nМожливі маршрути:")

    for i, route in enumerate(routes, 1):
        distance, time, traffic = route_info(route)

        print(
            f"{i}. {' -> '.join(route)} | "
            f"{distance} км | {time} хв"
        )

    choice = int(
        input("\nЯким маршрутом поїхали? ")
    ) - 1

    route = routes[choice]
    distance, time, traffic = route_info(route)

    cur.execute("""
        INSERT INTO routes(
            start,
            finish,
            route,
            distance,
            expected_time,
            traffic
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        start,
        finish,
        ",".join(route),
        distance,
        time,
        traffic
    ))

    db.commit()

    print("Маршрут збережено.")
    print("ID поїздки:", cur.lastrowid)


# ---------------- ACTUAL RESULT ----------------

def add_result():
    route_id = int(input("ID поїздки: "))
    actual_time = float(input("Фактичний час: "))
    actual_distance = float(input("Фактична відстань: "))

    cur.execute("""
        UPDATE routes
        SET actual_time=?, actual_distance=?
        WHERE id=?
    """, (
        actual_time,
        actual_distance,
        route_id
    ))

    db.commit()

    print("Результат збережено.")


# ---------------- HISTORY ----------------

def history():
    rows = cur.execute("""
        SELECT *
        FROM routes
    """).fetchall()

    for r in rows:
        print(r)


# ---------------- STATISTICS ----------------

def statistics():
    rows = cur.execute("""
        SELECT
            route,
            COUNT(*),
            AVG(expected_time),
            AVG(actual_time),
            AVG(actual_distance)

        FROM routes

        GROUP BY route
    """).fetchall()

    for r in rows:
        print("\nМаршрут:", r[0].replace(",", " -> "))
        print("Поїздок:", r[1])
        print("Середній прогноз:", r[2])
        print("Середній факт:", r[3])
        print("Середня відстань:", r[4])


# ---------------- AI ----------------

def ai():
    start = input("Початкова точка: ").upper()
    finish = input("Кінцева точка: ").upper()

    best = dijkstra(start, finish)

    rows = cur.execute("""
        SELECT
            route,
            COUNT(*),
            AVG(expected_time),
            AVG(actual_time)

        FROM routes

        WHERE start=? AND finish=?
        AND actual_time IS NOT NULL

        GROUP BY route
    """, (
        start,
        finish
    )).fetchall()

    if not rows:
        print("Недостатньо історичних даних.")
        return

    text = ""

    for r in rows:
        text += (
            f"Маршрут {r[0]}: "
            f"{r[1]} поїздок, "
            f"прогноз {r[2]:.1f} хв, "
            f"факт {r[3]:.1f} хв.\n"
        )

    prompt = f"""
/no_think

Ти AI-аналітик навігатора.

Dijkstra рекомендує:
{" -> ".join(best)}

Історія реальних поїздок:

{text}

Зроби короткий аналіз.

Правила:
1. Порівнюй маршрути за середнім фактичним часом.
2. Якщо альтернативний маршрут фактично швидший,
   рекомендуй його.
3. Якщо маршрут Dijkstra найшвидший,
   рекомендуй його.
4. Якщо для маршруту менше 3 поїздок,
   скажи, що даних ще мало.
5. Не вигадуй маршрути та числа.
6. Відповідай українською.

Формат:

Рекомендований маршрут:
...

Причина:
...
"""

    response = ollama.chat(
        model="qwen3:1.7b",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    print("\n===== AI =====")
    print(response["message"]["content"])


# ---------------- MENU ----------------

while True:
    print("""
===== AI NAVIGATOR =====

1. Знайти маршрут
2. Додати результат проходження
3. Історія маршрутів
4. Статистика
5. AI-рекомендація
0. Вихід
""")

    choice = input("> ")

    if choice == "1":
        find_route()

    elif choice == "2":
        add_result()

    elif choice == "3":
        history()

    elif choice == "4":
        statistics()

    elif choice == "5":
        ai()

    elif choice == "0":
        break


db.close()
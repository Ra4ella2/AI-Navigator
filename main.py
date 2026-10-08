import sqlite3


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
    difficulty REAL,
    actual_time REAL,
    actual_distance REAL
)
""")

db.commit()

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

def route_info(route):
    distance = 0
    time = 0
    traffic = 0
    difficulty = 0

    for i in range(len(route) - 1):
        road = graph[route[i]][route[i + 1]]

        distance += road[0]
        time += road[1]
        traffic += road[2]
        difficulty += road[3]

    parts = len(route) - 1

    return (
        distance,
        time,
        traffic / parts,
        difficulty / parts
    )

def find_route():
    start = input("Початкова точка: ").upper()
    finish = input("Кінцева точка: ").upper()

    if start not in graph or finish not in graph:
        print("Невірна точка.")
        return

    best = dijkstra(start, finish)

    print("\nDijkstra рекомендує:")
    print(" -> ".join(best))

    routes = find_all_routes(start, finish)

    routes.sort(key=lambda r: route_info(r)[0])

    routes = routes[:3]

    print("\nМожливі маршрути:")

    for i, route in enumerate(routes, 1):
        distance, time, traffic, difficulty = route_info(route)

        print(
            f"{i}. {' -> '.join(route)} | "
            f"{distance} км | {time} хв"
        )

    choice = int(input("\nЯким маршрутом поїхали? ")) - 1

    route = routes[choice]

    distance, time, traffic, difficulty = route_info(route)

    cur.execute("""
        INSERT INTO routes(
            start,
            finish,
            route,
            distance,
            expected_time,
            traffic,
            difficulty
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        start,
        finish,
        ",".join(route),
        distance,
        time,
        traffic,
        difficulty
    ))

    db.commit()

    print("Маршрут збережено.")
    print("ID поїздки:", cur.lastrowid)


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


def history():
    rows = cur.execute("""
        SELECT
            id,
            start,
            finish,
            route,
            distance,
            expected_time,
            actual_time,
            actual_distance
        FROM routes
    """).fetchall()

    for r in rows:
        print(
            f"ID: {r[0]} | "
            f"{r[1]} -> {r[2]} | "
            f"{r[3].replace(',', ' -> ')} | "
            f"прогноз: {r[5]} хв | "
            f"факт: {r[6]}"
        )


def statistics():
    rows = cur.execute("""
        SELECT
            route,
            COUNT(*),
            AVG(expected_time),
            AVG(actual_time),
            AVG(actual_distance),
            MIN(actual_time),
            MAX(actual_time)

        FROM routes

        GROUP BY route
    """).fetchall()

    print("\n===== СТАТИСТИКА =====")

    for r in rows:
        print("\nМаршрут:", r[0].replace(",", " -> "))
        print("Поїздок:", r[1])
        print("Середній прогноз:", r[2])
        print("Середній факт:", r[3])
        print("Середня відстань:", r[4])
        print("Найшвидший час:", r[5])
        print("Найповільніший час:", r[6])

def ai_recommendation():
    start = input("Початкова точка: ").upper()
    finish = input("Кінцева точка: ").upper()

    if start not in graph or finish not in graph:
        print("Невірна точка.")
        return

    dijkstra_route = dijkstra(start, finish)

    rows = cur.execute("""
        SELECT
            route,
            COUNT(*),
            AVG(expected_time),
            AVG(actual_time)

        FROM routes

        WHERE
            start = ?
            AND finish = ?
            AND actual_time IS NOT NULL

        GROUP BY route
    """, (
        start,
        finish
    )).fetchall()

    print("\n===== АНАЛІЗ СИСТЕМИ =====")

    print(
        "Dijkstra:",
        " -> ".join(dijkstra_route)
    )

    if not rows:
        print("Історичних даних поки немає.")
        print("Рекомендація: використати маршрут Dijkstra.")
        return

    best_route = None
    best_actual_time = float("inf")

    for route, count, expected, actual in rows:

        difference = actual - expected
        coefficient = actual / expected

        print("\nМаршрут:", route.replace(",", " -> "))
        print("Поїздок:", count)
        print("Прогноз:", round(expected, 1), "хв")
        print("Факт:", round(actual, 1), "хв")
        print("Різниця:", round(difference, 1), "хв")
        print("Коефіцієнт:", round(coefficient, 2))

        if difference > 0:
            percent = (coefficient - 1) * 100
            print(
                "Маршрут займає приблизно",
                round(percent, 1),
                "% більше часу, ніж прогноз."
            )

        elif difference < 0:
            percent = (1 - coefficient) * 100
            print(
                "Маршрут проходиться приблизно",
                round(percent, 1),
                "% швидше за прогноз."
            )

        else:
            print("Прогноз відповідає реальному часу.")

        if actual < best_actual_time:
            best_actual_time = actual
            best_route = route

    print("\n===== РЕКОМЕНДАЦІЯ =====")

    if best_route is None:
        print("Недостатньо даних для впевненої рекомендації.")
        print(
            "Поки що використовуйте:",
            " -> ".join(dijkstra_route)
        )

    else:
        print(
            "Рекомендований маршрут:",
            best_route.replace(",", " -> ")
        )

        print(
            "Середній фактичний час:",
            round(best_actual_time, 1),
            "хв"
        )

        if best_route == ",".join(dijkstra_route):
            print(
                "Маршрут Dijkstra підтверджується історичними даними."
            )
        else:
            print(
                "За історичними даними цей маршрут швидший за стандартний маршрут Dijkstra."
            )

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
        ai_recommendation()

    elif choice == "0":
        break


db.close()
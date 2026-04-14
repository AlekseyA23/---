from flask import Flask, render_template, request, jsonify
import sqlite3
import json

app = Flask(__name__)
DB_NAME = "skat_final.db"

# ---------- ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ ----------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS pathogens (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        risk_group TEXT,
        drug_sensitivity TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS empiric_protocols (
        id INTEGER PRIMARY KEY,
        localization TEXT NOT NULL,
        stratification TEXT NOT NULL,
        first_line TEXT,
        second_line TEXT,
        third_line TEXT,
        allergy_alternative TEXT,
        renal_alternative TEXT,
        note TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS risk_factors (
        id INTEGER PRIMARY KEY,
        factor_name TEXT UNIQUE,
        associated_risk TEXT,
        weight INTEGER)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS drugs (
        id INTEGER PRIMARY KEY,
        name TEXT UNIQUE,
        typical_dose TEXT,
        renal_adjustment TEXT,
        pregnancy_category TEXT)''')
    
    # Заполнение данными, если пусто
    cur.execute("SELECT COUNT(*) FROM risk_factors")
    if cur.fetchone()[0] == 0:
        factors = [
            ("ИВЛ > 5 дней", "pseudomonas", 2),
            ("Предшествующие антибиотики (цефалоспорины/фторхинолоны)", "mrsa", 2),
            ("Колонизация/инфекция МРЗС в анамнезе", "mrsa", 3),
            ("Нейтропения (<500)", "pseudomonas", 2),
            ("Катетер центральной вены >7 дней", "mrsa", 1),
            ("Послеоперационная рана (абдоминальная)", "anaerobes", 2),
            ("Длительная госпитализация (>14 дней)", "pseudomonas", 2),
        ]
        cur.executemany("INSERT INTO risk_factors (factor_name, associated_risk, weight) VALUES (?,?,?)", factors)
    
    cur.execute("SELECT COUNT(*) FROM empiric_protocols")
    if cur.fetchone()[0] == 0:
        protocols = [
            ("Пневмония", "community_acquired", "Амоксициллин/клавуланат", "Цефтриаксон + Азитромицин", "Левофлоксацин", "Макролиды (при аллергии на пенициллины)", "Цефтриаксон 1 г/сут при CrCl<30", "Учитывать аллергию"),
            ("Пневмония", "early_nosocomial", "Цефтриаксон", "Левофлоксацин", "Моксифлоксацин", "Азитромицин + цефтриаксон", "Цефтриаксон 1 г/сут при CrCl<30", "Длительность госпитализации <5 дней"),
            ("Пневмония", "late_nosocomial_mrsa", "Линезолид + Цефепим", "Ванкомицин + Пиперациллин/тазобактам", "Тигециклин + Цефепим", "Линезолид (при аллергии на ванкомицин)", "Коррекция цефепима при CrCl<60", "Покрытие МРЗС и грам-отрицательных"),
            ("Пневмония", "late_nosocomial_pseudomonas", "Пиперациллин/тазобактам", "Меропенем + Амикацин", "Цефепим + Амикацин", "Колистин + меропенем", "Коррекция всех препаратов по CrCl", "Риск синегнойной инфекции"),
            ("Интраабдоминальная инфекция", "community_acquired", "Цефтриаксон + Метронидазол", "Левофлоксацин + Метронидазол", "Моксифлоксацин моно", "Метронидазол + амоксициллин/клавуланат", "Метронидазол без коррекции", "Альтернатива: тигециклин"),
            ("Интраабдоминальная инфекция", "late_nosocomial_mrsa", "Ванкомицин + Пиперациллин/тазобактам", "Тигециклин", "Линезолид + Меропенем", "Даптомицин + метронидазол", "Коррекция ванкомицина и пиперациллина", "Тяжелое течение + риск МРЗС"),
            ("Интраабдоминальная инфекция", "late_nosocomial_pseudomonas", "Меропенем", "Пиперациллин/тазобактам + Амикацин", "Цефепим + Метронидазол", "Колистин + меропенем", "Коррекция по CrCl", "При перфорации + анаэробы покрыты"),
            ("ИМВП", "community_acquired", "Цефтриаксон", "Левофлоксацин", "Фосфомицин (однократно)", "Нитрофурантоин (при цистите)", "Цефтриаксон 1 г/сут при CrCl<30", "При цистите возможно фосфомицин однократно"),
            ("ИМВП", "late_nosocomial_mrsa", "Ванкомицин (при катетере)", "Линезолид", "Даптомицин", "Рифампицин + котримоксазол", "Ванкомицин по CrCl", "Энтерококковая инфекция возможна"),
            ("ИМВП", "late_nosocomial_pseudomonas", "Пиперациллин/тазобактам", "Цефепим", "Меропенем", "Амикацин", "Коррекция всех препаратов", "Часто P. aeruginosa у катетерных"),
            ("Сепсис", "early_nosocomial", "Пиперациллин/тазобактам", "Цефтриаксон + Метронидазол", "Меропенем", "Ванкомицин + цефтриаксон", "Коррекция по CrCl", "Деэскалация через 48ч"),
            ("Сепсис", "late_nosocomial_mrsa", "Ванкомицин + Пиперациллин/тазобактам", "Меропенем + Линезолид", "Цефепим + Линезолид + Метронидазол", "Даптомицин + меропенем", "Коррекция всех", "Эмпирически широкий спектр"),
            ("Сепсис", "late_nosocomial_pseudomonas", "Меропенем + Амикацин", "Цефепим + Амикацин", "Пиперациллин/тазобактам + тобрамицин", "Колистин + меропенем", "Коррекция всех", "При септическом шоке + коломицин"),
        ]
        cur.executemany("INSERT INTO empiric_protocols (localization, stratification, first_line, second_line, third_line, allergy_alternative, renal_alternative, note) VALUES (?,?,?,?,?,?,?,?)", protocols)

    cur.execute("SELECT COUNT(*) FROM drugs")
    if cur.fetchone()[0] == 0:
        drugs = [
            ("Цефтриаксон", "1-2 г в/в 1 р/сут", "Клир. креат. >30: без изменений; <30: 1 г/сут", "C"),
            ("Меропенем", "1 г в/в 3 р/сут (до 2 г 3 р/сут)", "Клир. креат. 26-50: 1 г 2 р/сут; 10-25: 0.5 г 2 р/сут; <10: 0.5 г 1 р/сут", "B"),
            ("Пиперациллин/тазобактам", "4.5 г в/в 3-4 р/сут", "Клир. креат. 20-40: 4.5 г 2 р/сут; <20: 4.5 г 1 р/сут", "B"),
            ("Ванкомицин", "15-20 мг/кг каждые 8-12ч, мониторинг", "Коррекция по клиренсу креатинина (интервал)", "C"),
            ("Линезолид", "600 мг в/в или внутрь 2 р/сут", "Коррекции не требуется", "C"),
            ("Левофлоксацин", "500 мг 1-2 р/сут", "Клир. креат. 20-49: 250 мг 1-2 р/сут; <20: 250 мг 1 р/сут", "C"),
            ("Амикацин", "15-20 мг/кг 1 р/сут", "Удлинение интервала при клир. <60", "D"),
            ("Цефепим", "1-2 г в/в 2-3 р/сут", "Клир. креат. 30-60: 1-2 г 2 р/сут; 11-29: 1-2 г 1 р/сут; <10: 0.5-1 г 1 р/сут", "B"),
            ("Метронидазол", "500 мг в/в 3 р/сут", "Коррекции не требуется", "B"),
        ]
        cur.executemany("INSERT INTO drugs (name, typical_dose, renal_adjustment, pregnancy_category) VALUES (?,?,?,?)", drugs)

    cur.execute("SELECT COUNT(*) FROM pathogens")
    if cur.fetchone()[0] == 0:
        pathogens = [
            ("E. coli (чувств.)", "low_risk", '{"цефтриаксон":"S","амоксициллин/клавуланат":"S","меропенем":"S"}'),
            ("E. coli (ESBL)", "late_nosocomial_mrsa", '{"цефтриаксон":"R","меропенем":"S","амикацин":"S"}'),
            ("K. pneumoniae (ESBL)", "late_nosocomial_mrsa", '{"цефтриаксон":"R","меропенем":"S","амикацин":"S"}'),
            ("P. aeruginosa (чувств.)", "late_nosocomial_pseudomonas", '{"пиперациллин/тазобактам":"S","меропенем":"S","цефепим":"S","амикацин":"S"}'),
            ("P. aeruginosa (MDR)", "late_nosocomial_pseudomonas", '{"пиперациллин/тазобактам":"R","меропенем":"I","цефепим":"R","амикацин":"S","колистин":"S"}'),
            ("S. aureus (MRSA)", "late_nosocomial_mrsa", '{"оксациллин":"R","ванкомицин":"S","линезолид":"S"}'),
            ("S. aureus (MSSA)", "low_risk", '{"оксациллин":"S","цефтриаксон":"S","ванкомицин":"S"}'),
        ]
        cur.executemany("INSERT INTO pathogens (name, risk_group, drug_sensitivity) VALUES (?,?,?)", pathogens)
    
    conn.commit()
    conn.close()

# ---------- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ----------
def calculate_crcl(age, weight, serum_creatinine, sex):
    if serum_creatinine > 20:
        scr_mgdl = serum_creatinine / 88.4
    else:
        scr_mgdl = serum_creatinine
    numerator = (140 - age) * weight
    denominator = 72 * scr_mgdl
    crcl = numerator / denominator
    if sex == 'female':
        crcl *= 0.85
    return max(crcl, 5)

def interpret_sofa(sofa_score):
    if sofa_score < 2:
        return "Низкий риск смертности (<10%)"
    elif sofa_score < 6:
        return "Умеренный риск (10-20%)"
    elif sofa_score < 12:
        return "Высокий риск (30-40%)"
    else:
        return "Очень высокий риск (>50%)"

def interpret_lab_markers(leukocytes, esr, pct):
    result = []
    if leukocytes == "<4.0":
        result.append("Лейкопения — возможна вирусная инфекция, сепсис.")
    elif leukocytes == "4.0-10.0":
        result.append("Лейкоциты в норме — не исключает бактериальную инфекцию.")
    elif leukocytes == "10.0-15.0":
        result.append("Умеренный лейкоцитоз — характерен для бактериальной инфекции.")
    elif leukocytes == ">15.0":
        result.append("Выраженный лейкоцитоз — высокая вероятность бактериальной инфекции.")
    if esr == "<10":
        result.append("СОЭ в норме — маловероятно активное воспаление.")
    elif esr == "10-30":
        result.append("СОЭ умеренно повышена.")
    elif esr == "30-60":
        result.append("СОЭ значительно повышена — характерно для бактериальных инфекций.")
    elif esr == ">60":
        result.append("СОЭ резко повышена — тяжелая инфекция, сепсис.")
    if pct == "<0.1":
        result.append("Прокальцитонин <0.1 — бактериальная инфекция маловероятна.")
    elif pct == "0.1-0.25":
        result.append("Прокальцитонин 0.1-0.25 — локальная инфекция возможна.")
    elif pct == "0.25-0.5":
        result.append("Прокальцитонин 0.25-0.5 — высокая вероятность бактериальной инфекции.")
    elif pct == ">0.5":
        result.append("Прокальцитонин >0.5 — бактериальная инфекция очень вероятна.")
    return result

def determine_stratification(localization, hospital_days, risk_factors_list):
    if hospital_days < 2:
        return "community_acquired"
    elif hospital_days <= 7:
        return "early_nosocomial"
    else:
        has_mrsa = any(f in ["Предшествующие антибиотики (цефалоспорины/фторхинолоны)", "Колонизация/инфекция МРЗС в анамнезе", "Катетер центральной вены >7 дней"] for f in risk_factors_list)
        has_pseudomonas = any(f in ["ИВЛ > 5 дней", "Нейтропения (<500)", "Длительная госпитализация (>14 дней)"] for f in risk_factors_list)
        if has_mrsa:
            return "late_nosocomial_mrsa"
        elif has_pseudomonas:
            return "late_nosocomial_pseudomonas"
        else:
            return "early_nosocomial"

def get_empiric_recommendation(localization, stratification):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT first_line, second_line, third_line, allergy_alternative, renal_alternative, note FROM empiric_protocols WHERE localization LIKE ? AND stratification = ?", (f"%{localization}%", stratification))
    row = cur.fetchone()
    conn.close()
    if row:
        return {"first_line": row[0], "second_line": row[1], "third_line": row[2], "allergy_alternative": row[3], "renal_alternative": row[4], "note": row[5]}
    return None

def get_targeted_recommendation(pathogen_name, risk_group=None):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    if risk_group:
        cur.execute("SELECT drug_sensitivity FROM pathogens WHERE name = ? AND risk_group = ?", (pathogen_name, risk_group))
    else:
        cur.execute("SELECT drug_sensitivity FROM pathogens WHERE name = ?", (pathogen_name,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return None
    sens = json.loads(row[0])
    sensitive = [d for d, s in sens.items() if s == "S"]
    result = []
    for drug in sensitive[:4]:
        cur2 = conn.cursor()
        cur2.execute("SELECT typical_dose, renal_adjustment FROM drugs WHERE name = ?", (drug,))
        drug_row = cur2.fetchone()
        dose = drug_row[0] if drug_row else "дозу уточните"
        renal_adj = drug_row[1] if drug_row else ""
        result.append({"drug": drug, "dose": dose, "renal_adjustment": renal_adj})
    conn.close()
    return result

def check_allergy_alert(drugs_list, allergy_history):
    if not allergy_history or allergy_history.lower() == "нет":
        return None
    allergy_lower = allergy_history.lower()
    warnings = []
    for drug in drugs_list:
        if "пенициллин" in allergy_lower and drug.lower() in ["амоксициллин/клавуланат", "пиперациллин/тазобактам"]:
            warnings.append(f"Перекрёстная аллергия на {drug} (пенициллины)")
        if "цефалоспорин" in allergy_lower and drug.lower() in ["цефтриаксон", "цефепим"]:
            warnings.append(f"Перекрёстная аллергия на {drug} (цефалоспорины)")
    return warnings if warnings else None

# ---------- FLASK РОУТЫ ----------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/risk_factors', methods=['GET'])
def get_risk_factors():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT factor_name FROM risk_factors")
    factors = [row[0] for row in cur.fetchall()]
    conn.close()
    return jsonify(factors)

@app.route('/api/empiric', methods=['POST'])
def empiric():
    data = request.get_json()
    localization = data.get('localization')
    hospital_days = float(data.get('hospital_days', 0))
    selected_factors = data.get('risk_factors', [])
    allergy = data.get('allergy', '')
    age = data.get('age', 60)
    weight = data.get('weight', 70)
    scr = data.get('serum_creatinine', 80)
    sex = data.get('sex', 'male')
    sofa = int(data.get('sofa_score', 0))
    leukocytes = data.get('leukocytes', '4.0-10.0')
    esr = data.get('esr', '10-30')
    pct = data.get('pct', '<0.1')
    
    if not localization:
        return jsonify({"error": "Выберите локализацию"}), 400
    
    crcl = calculate_crcl(age, weight, scr, sex)
    stratification = determine_stratification(localization, hospital_days, selected_factors)
    rec = get_empiric_recommendation(localization, stratification)
    if not rec:
        return jsonify({"error": f"Нет протокола для локации '{localization}' и стратификации '{stratification}'"}), 404
    
    lab_interpretation = interpret_lab_markers(leukocytes, esr, pct)
    allergy_warnings = check_allergy_alert([rec["first_line"], rec["second_line"]], allergy)
    
    return jsonify({
        "type": "empiric",
        "stratification": stratification,
        "first_line": rec["first_line"],
        "second_line": rec["second_line"],
        "third_line": rec["third_line"],
        "allergy_alternative": rec["allergy_alternative"],
        "renal_alternative": rec["renal_alternative"],
        "note": rec["note"],
        "crcl": round(crcl, 1),
        "sofa_score": sofa,
        "sofa_interpretation": interpret_sofa(sofa),
        "lab_interpretation": lab_interpretation,
        "allergy_warnings": allergy_warnings
    })

@app.route('/api/targeted', methods=['POST'])
def targeted():
    data = request.get_json()
    pathogen = data.get('pathogen', '').strip()
    risk_group = data.get('risk_group', '')
    allergy = data.get('allergy', '')
    crcl = data.get('crcl', None)
    if not pathogen:
        return jsonify({"error": "Выберите возбудителя"}), 400
    
    rec = get_targeted_recommendation(pathogen, risk_group if risk_group else None)
    if rec is None:
        return jsonify({"error": f"Нет данных о чувствительности для {pathogen}"}), 404
    
    allergy_warnings = check_allergy_alert([r["drug"] for r in rec], allergy)
    return jsonify({
        "type": "targeted",
        "pathogen": pathogen,
        "recommendations": rec,
        "allergy_warnings": allergy_warnings
    })

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=8080)

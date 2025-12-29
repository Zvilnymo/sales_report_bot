from b24 import B24
import requests
from datetime import datetime, timedelta
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import os

# --- для корректных границ дня по Киеву
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # pip install backports.zoneinfo


b24 = B24(domain=os.getenv("B24_DOMAIN"), user_id=int(os.getenv("B24_USER_ID")), token=os.getenv("B24_TOKEN_1"))

category_id = 0

yesterday = (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d')

deal_filter = {
    "CATEGORY_ID": category_id, 
    ">=CLOSEDATE": f'{yesterday}T00:00:01',  
    "<=CLOSEDATE": f'{yesterday}T23:59:59',
    'STAGE_ID': 'WON'
}

select_fields = ["ID", "OPPORTUNITY", 'ASSIGNED_BY_ID', 'CLOSEDATE', 'UTM_SOURCE', 'UF_CRM_1695636781']  

deals = b24.get_list("crm.deal.list", b24_filter=deal_filter, select=select_fields)
deals_list = pd.DataFrame(deals)

#Выгружаем данные по менеджерам из СRM
b24 = B24(os.getenv("B24_DOMAIN"), int(os.getenv("B24_USER_ID")), os.getenv("B24_TOKEN_2"))
items_users = b24.get_list('user.get', select=['ID','NAME', 'LAST_NAME', 'SECOND_NAME'])
users_df = pd.DataFrame(items_users)[['ID', 'NAME', 'LAST_NAME', 'SECOND_NAME']]
users_df['FULL_NAME'] = users_df[['NAME', 'LAST_NAME', 'SECOND_NAME']].fillna('').agg(' '.join, axis=1).str.strip()
users_df = users_df[['ID', 'FULL_NAME']]

#Преобразовуем данные 
full_data = deals_list.merge(users_df, how='inner', left_on='ASSIGNED_BY_ID', right_on='ID')
full_data["OPPORTUNITY"] = full_data["OPPORTUNITY"].astype(float)
full_data = full_data.rename(columns={'ID_x':'deal_id','OPPORTUNITY':'contract_amount','FULL_NAME':'manager','UF_CRM_1695636781':'type_contract'})
full_data.type_contract = full_data.type_contract.replace({'1206':'Банкрутсво','1207':'Досудове'})

#Анализ данных по типу контакта
type_contacts_data = full_data.groupby('type_contract') \
        .agg({'contract_amount':'sum','deal_id':'count'}) \
        .reset_index() \
        .rename(columns={'deal_id':'number_of_contracts'})


#Анализ данных по менеджерам
data_sales_by_managers = full_data.groupby('manager') \
        .aggregate({'contract_amount':'sum','CLOSEDATE':'count'}) \
        .sort_values('contract_amount', ascending=False) \
        .reset_index() \
        .rename(columns={'CLOSEDATE':'number_of_contracts'})

#Анализ данных по источникам
data_sales_by_source = full_data.groupby('UTM_SOURCE') \
        .aggregate({'contract_amount':'sum','CLOSEDATE':'count'}) \
        .sort_values('contract_amount', ascending=False) \
        .reset_index() \
        .rename(columns={'CLOSEDATE':'number_of_contracts'})

# Рассчитываем общее количество продаж за сегодня
total_sales_yesterday = full_data.contract_amount.sum()

# Создаем фигуру с 2 строками и 2 столбцами
fig, axes = plt.subplots(2, 2, figsize=(14, 12))

# 1-й график: Продажи по менеджерам (сумма контрактов)
data_sales_by_managers = data_sales_by_managers.sort_values(by="contract_amount", ascending=False)  # Сортируем по убыванию
ax1 = axes[0, 0]
ax1.bar(data_sales_by_managers['manager'], data_sales_by_managers['contract_amount'], 
        color='skyblue', edgecolor='black', label="Сумма контрактов")
for i, amount in enumerate(data_sales_by_managers['contract_amount']):
    ax1.text(i, amount, f'{amount:,.0f}', va='bottom', ha='center', fontsize=12, fontweight='bold', color='black')
ax1.set_title('Продажи по менеджерам (сумма контрактов)', fontsize=14, fontweight='bold')
ax1.set_xlabel('Менеджер', fontsize=12, fontweight='bold')
ax1.set_ylabel('Сумма контрактов', fontsize=12, fontweight='bold')
ax1.set_xticklabels(data_sales_by_managers['manager'], rotation=45, ha='right')
for spine in ax1.spines.values():
    spine.set_visible(False)

# 2-й график: Продажи по менеджерам (количество контрактов)
ax2 = axes[0, 1]
ax2.bar(data_sales_by_managers['manager'], data_sales_by_managers['number_of_contracts'], 
        color='lightblue', edgecolor='black', label="Количество контрактов")
for i, contracts in enumerate(data_sales_by_managers['number_of_contracts']):
    ax2.text(i, contracts, f'{contracts}', va='bottom', ha='center', fontsize=12, fontweight='bold', color='black')
ax2.set_title('Продажи по менеджерам (количество контрактов)', fontsize=14, fontweight='bold')
ax2.set_xlabel('Менеджер', fontsize=12, fontweight='bold')
ax2.set_ylabel('Количество контрактов', fontsize=12, fontweight='bold')
ax2.set_xticklabels(data_sales_by_managers['manager'], rotation=45, ha='right')
for spine in ax2.spines.values():
    spine.set_visible(False)

# 3-й график: Продажи по источникам (сумма контрактов)
data_sales_by_source = data_sales_by_source.sort_values(by="contract_amount", ascending=False)  # Сортируем по убыванию
ax3 = axes[1, 0]
ax3.bar(data_sales_by_source['UTM_SOURCE'], data_sales_by_source['contract_amount'], 
        color='skyblue', edgecolor='black', label="Сумма контрактов")
for i, amount in enumerate(data_sales_by_source['contract_amount']):
    ax3.text(i, amount, f'{amount:,.0f}', va='bottom', ha='center', fontsize=12, fontweight='bold', color='black')
ax3.set_title('Продажи по источникам (сумма контрактов)', fontsize=14, fontweight='bold')
ax3.set_xlabel('Источник', fontsize=12, fontweight='bold')
ax3.set_ylabel('Сумма контрактов', fontsize=12, fontweight='bold')
ax3.set_xticklabels(data_sales_by_source['UTM_SOURCE'], rotation=45, ha='right')
for spine in ax3.spines.values():
    spine.set_visible(False)

# 4-й график: Продажи по источникам (количество контрактов)
ax4 = axes[1, 1]
ax4.bar(data_sales_by_source['UTM_SOURCE'], data_sales_by_source['number_of_contracts'], 
        color='lightblue', edgecolor='black', label="Количество контрактов")
for i, contracts in enumerate(data_sales_by_source['number_of_contracts']):
    ax4.text(i, contracts, f'{contracts}', va='bottom', ha='center', fontsize=12, fontweight='bold', color='black')
ax4.set_title('Продажи по источникам (количество контрактов)', fontsize=14, fontweight='bold')
ax4.set_xlabel('Источник', fontsize=12, fontweight='bold')
ax4.set_ylabel('Количество контрактов', fontsize=12, fontweight='bold')
ax4.set_xticklabels(data_sales_by_source['UTM_SOURCE'], rotation=45, ha='right')
for spine in ax4.spines.values():
    spine.set_visible(False)

fig.text(0.5, 1.05, f'Общее количество продаж за вчерашний день: {total_sales_yesterday:,.0f} UAH', 
         ha='center', fontsize=20, fontweight='bold', color='darkblue')
plt.tight_layout()
fig.savefig('sales_report.png', bbox_inches='tight', dpi=300)

# ---------------------- ФИНМАП: одна строка за вчера -------------------------
FINMAP_API_KEY = os.getenv("FINMAP_API_KEY")       # добавишь на Render
FINMAP_COMPANY_ID = os.getenv("FINMAP_COMPANY_ID") # добавишь на Render
FINMAP_URL = "https://api.finmap.online/v2.2/operations/list"

def finmap_yesterday_line():
    """
    Возвращает строку вида:
    '💵 Фактичні надходження (Finmap, YYYY-MM-DD): <b>*.** грн</b> (операцій: N)'
    или '' (если ключей нет или запрос не удался).
    """
    if not FINMAP_API_KEY:
        return ""

    kyiv = ZoneInfo("Europe/Kyiv")
    today0 = datetime.now(kyiv).replace(hour=0, minute=0, second=0, microsecond=0)
    yest0  = today0 - timedelta(days=1)
    start_ms, end_ms = int(yest0.timestamp())*1000, int(today0.timestamp())*1000
    date_label = yest0.date().isoformat()

    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "apiKey": FINMAP_API_KEY,
    }
    if FINMAP_COMPANY_ID:
        headers["X-Company-Id"] = FINMAP_COMPANY_ID

    limit, offset = 100, 0  # ограничение API
    use_alt_dates = False
    total = 0.0
    count = 0

    while True:
        body = {
            "limit": limit,
            "offset": offset,
            "useDateOfPayment": True,
            "approved": True,
            "types": ["income"],
            "desc": True,
            "field": "date",
        }
        if not use_alt_dates:
            body.update({"startDate": start_ms, "endDate": end_ms})
        else:
            body.update({"dateFrom": start_ms, "dateTo": end_ms})

        r = requests.post(FINMAP_URL, json=body, headers=headers, timeout=30)

        if r.status_code in (400, 422) and not use_alt_dates:
            use_alt_dates = True
            continue

        if not (200 <= r.status_code < 300):
            # не ломаем логику отчета — просто вернем пустую строку
            return ""

        data = r.json()
        rows = data.get("list") or data.get("items") or []
        for it in rows:
            # суммируем в валюте компании, если поле есть
            amt = float(it.get("companyCurrencySum") or it.get("amount") or it.get("sum") or 0)
            total += amt
        count += len(rows)

        if len(rows) < limit:
            break
        offset += len(rows)

    return f"\n\n💵 Фактичні надходження (Finmap, {date_label}): <b>{total:,.2f} грн</b> (операцій: {count})"

#Отправляем данные в телеграм бота
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
chat_ids = [727013047, 718885452, 6775209607, 1139941966, 332270956]

def send_message(text, chat_ids):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    for chat_id in chat_ids:
        requests.post(url, data={"chat_id": chat_id, "text": text, "parse_mode": "HTML"})

def send_graph_to_telegram(image_path, chat_ids):
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    for chat_id in chat_ids:
        with open(image_path, "rb") as photo:
            requests.post(url, data={"chat_id": chat_id}, files={"photo": photo})

# Рассчитываем общее количество продаж за вчерашний день
total_sales_yesterday = full_data.contract_amount.sum()

# Создаем условие для проверки, были ли продажи
if full_data.shape[0] == 0:
    message_text = "🔴 СЕГОДНЯ БЕЗ ПРОДАЖ, ПРИБЫЛЬ СОСТАВИЛА 0 ГРН!!!! 🔴"
else:
    message_text = (
        f"📊 Это отчет по продажам за <b>{yesterday}</b>.\n"
        f"💰 Вчера было совершено <b>{full_data.shape[0]}</b> продаж.\n"
        f"💸 На сумму <b>{full_data['contract_amount'].sum()}</b>\n\n"
        + "\n".join(
            f"🔹 {row['type_contract']}: {row['contract_amount']} (Контрактов: {row['number_of_contracts']})"
            for _, row in type_contacts_data.iterrows()
        )
    )

# >>> добавляем одну финальную строку с фактичними надходженнями из Finmap:
message_text += finmap_yesterday_line()

# Отправляем график и сообщение в Telegram
send_graph_to_telegram("sales_report.png", chat_ids)
send_message(message_text, chat_ids)

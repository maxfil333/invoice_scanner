import os
import json
import pandas as pd

from config.config import config


# ___ creates excel file from old unique_services ___


# Берем существующий "unique_comments.json"
unique_comments = os.path.join(config['BASE_DIR'], 'config', 'unique_comments.json')
with open(unique_comments, 'r', encoding='utf-8') as file:
    dct = json.load(file)

# формируем список кортежей типа [(id_, comment, service, code), ...]
results = []
for d in dct:
    id_ = d['id']
    comment = d['comment']
    service_code_list = d['service_code']
    for service_code in service_code_list:
        split = [x for x in service_code.split('#') if x]
        service, code = split[0], split[-1]
        results.append((id_, comment, service, code))


# сохраняем в excel
columns = ['id', 'comment', 'service', 'code']
df = pd.DataFrame(results, columns=columns)
df.to_excel(r"excel_file.xlsx", index=False)

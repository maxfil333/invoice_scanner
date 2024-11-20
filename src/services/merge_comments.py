import json


def merge(file1: str, file2: str, out_file: str = "merged_unique_comments.json"):

    with open(file1, 'r', encoding='utf-8') as f:
        data1: list[dict] = json.load(f)
        data1_comments = [x['comment'] for x in data1]
        last_id = data1[-1]['id']

    with open(file2, 'r', encoding='utf-8') as f:
        data2: list[dict] = json.load(f)

    for d in data2:
        new_comment = d['comment']
        if new_comment not in data1_comments:
            last_id += 1
            d['id'] = last_id
            data1.append(d)

    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(data1, f, ensure_ascii=False, indent=4)


if __name__ == '__main__':
    file1 = r'C:\Users\Filipp\PycharmProjects\Invoice_scanner\config\unique_comments.json'
    file2 = r'C:\Users\Filipp\PycharmProjects\Invoice_scanner\src\services\new_unique_comments.json'

    merge(file1, file2)

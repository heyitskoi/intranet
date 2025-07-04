import csv
import sys
import os

def is_float(val):
    try:
        float(val)
        return True
    except Exception:
        return False

def clean_overtime_csv(input_path):
    base, ext = os.path.splitext(input_path)
    output_path = f"{base}-cleaned{ext}"
    with open(input_path, newline='', encoding='utf-8') as infile:
        reader = list(csv.reader(infile))
        if not reader:
            print(f"File {input_path} is empty.")
            return
        header = reader[0]
        rows = reader[1:]
        duration_idx = None
        try:
            duration_idx = header.index('duration_hours')
        except ValueError:
            print("No 'duration_hours' column found in header!")
            return
        good_rows = []
        bad_rows = []
        for i, row in enumerate(rows, 2):  # 2 = line number in file
            if len(row) != len(header):
                bad_rows.append((i, row, 'Wrong number of columns'))
                continue
            if not is_float(row[duration_idx]):
                bad_rows.append((i, row, f"duration_hours not a float: {row[duration_idx]}"))
                continue
            good_rows.append(row)
    with open(output_path, 'w', newline='', encoding='utf-8') as outfile:
        writer = csv.writer(outfile)
        writer.writerow(header)
        writer.writerows(good_rows)
    print(f"Kept {len(good_rows)} rows, skipped {len(bad_rows)} bad rows. Output file: {output_path}")
    if bad_rows:
        print("Bad rows:")
        for line_num, row, reason in bad_rows:
            print(f"  Line {line_num}: {reason} | {row}")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python clean_overtime_csv.py <csv_file_path>")
        sys.exit(1)
    clean_overtime_csv(sys.argv[1]) 
import csv
import uuid
import sys
import os


def fix_overtime_csv(input_path):
    # Determine output path
    base, ext = os.path.splitext(input_path)
    output_path = f"{base}-fixed{ext}"

    with open(input_path, newline='', encoding='utf-8') as infile:
        reader = list(csv.reader(infile))
        if not reader:
            print(f"File {input_path} is empty.")
            return
        header = reader[0]
        rows = reader[1:]

        # Check if 'id' column exists
        if 'id' in header:
            print(f"File {input_path} already has an 'id' column. No changes made.")
            return

        # Add 'id' as the first column
        new_header = ['id'] + header
        new_rows = []
        for row in rows:
            new_rows.append([str(uuid.uuid4())] + row)

    with open(output_path, 'w', newline='', encoding='utf-8') as outfile:
        writer = csv.writer(outfile)
        writer.writerow(new_header)
        writer.writerows(new_rows)

    print(f"Updated {len(new_rows)} rows. Output file: {output_path}")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python fix_overtime_csv.py <csv_file_path>")
        sys.exit(1)
    fix_overtime_csv(sys.argv[1]) 
"""
Chốt chặn bí mật cho repo thực tập (pre-commit).

Chặn commit khi:
  - có tệp .env, *.pem, thư mục .aws/ hoặc du_lieu/ trong danh sách commit;
  - có dòng thêm mới chứa GIÁ TRỊ của bất kỳ biến nào trong .env (key TomTom, khóa AWS…).

Không in giá trị bí mật ra màn hình — chỉ báo tên biến và tên tệp.
"""
import os
import subprocess
import sys

GOC = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True).stdout.strip()


def gia_tri_bi_mat():
    ra = {}
    tep = os.path.join(GOC, '.env')
    if os.path.exists(tep):
        for dong in open(tep, encoding='utf-8'):
            dong = dong.strip()
            if '=' in dong and not dong.startswith('#'):
                k, v = dong.split('=', 1)
                v = v.strip().strip('"').strip("'")
                if len(v) >= 8:
                    ra[k.strip()] = v
    return ra


def main():
    tep_commit = subprocess.run(['git', 'diff', '--cached', '--name-only'],
                                capture_output=True, text=True, encoding='utf-8').stdout.split('\n')
    loi = []
    for t in filter(None, tep_commit):
        ten = t.replace('\\', '/')
        if ten == '.env' or ten.endswith('/.env') or ten.endswith('.pem') \
                or ten.startswith('du_lieu/') or '/.aws/' in '/' + ten:
            loi.append(f'khong duoc commit tep: {ten}')

    bi_mat = gia_tri_bi_mat()
    if bi_mat:
        khac = subprocess.run(['git', 'diff', '--cached', '-U0'], capture_output=True,
                              text=True, encoding='utf-8', errors='replace').stdout
        tep_hien = '?'
        for dong in khac.split('\n'):
            if dong.startswith('+++ '):
                tep_hien = dong[6:] if dong.startswith('+++ b/') else dong[4:]
            elif dong.startswith('+') and not dong.startswith('+++'):
                for ten, gt in bi_mat.items():
                    if gt in dong:
                        loi.append(f'{tep_hien}: co gia tri cua bien {ten} trong .env')

    if loi:
        print('CHAN COMMIT — co bi mat:', file=sys.stderr)
        for l in sorted(set(loi)):
            print('  ' + l, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())

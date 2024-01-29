"""課題1用テスト"""
import os
import sys
import re
from pathlib import Path
import glob
import subprocess
import pytest
import itertools


TARGET = "tc"
TARGETPATH = "/workspaces"

class ScanError(Exception):
    """字句解析エラーハンドラ"""

def command(cmd):
    """コマンドの実行"""
    try:
        result = subprocess.run(cmd, shell=True, check=False,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                universal_newlines=True)
#        for line in result.stdout.splitlines():
#            yield line
        return [result.stdout,result.stderr]
    except subprocess.CalledProcessError:
        print(f"外部プログラムの実行に失敗しました [{cmd}]", file=sys.stderr)
        sys.exit(1)

def common_task(mpl_file, out_file):
    """共通して実行するタスク"""
    try:
#        tc = Path(__file__).parent.parent.joinpath("tc")
        exe = Path(TARGETPATH) / Path(TARGET)
        exec_res = command(f"{exe} {mpl_file}")
        out = []
        sout = exec_res.pop(0)
        serr = exec_res.pop(0)
        if serr:
            raise ScanError(serr)
        for line in sout.splitlines():
            if re.search(r'Identifier',line):
                continue
#            if re.search(r'StringLiteral',line):
#                continue
#            if re.search(r'NumberLiteral',line):
#                continue
            if re.search(r'\s*"\s*\S*\s*"\s*\d+\s*',line):
                formatted = re.sub(r'\s*"\s*(\S*)\s*"\s*(\d+)\s*', r'"\1"\t\2\n', line)
                out.append(formatted)
        out.sort()
        with open(out_file, mode='w',encoding='utf-8') as fp:
            for l in out:
                fp.write(l)
        return 0
    except ScanError as exc:
        if re.search(r'sample0', mpl_file):
            for line in serr.splitlines():
                out.append(line)
            with open(out_file, mode='w',encoding='utf-8') as fp:
                for l in out:
                    fp.write(l+'\n')
            return 1
        raise ScanError(serr) from exc
    except Exception as err:
        with open(out_file, mode='w',encoding='utf-8') as fp:
            print(err, file=fp)
        raise err

# ===================================
# pytest code
# ===================================

TEST_RESULT_DIR = "test_results"
TEST_EXPECT_DIR = "test_expects"

test_data = sorted(glob.glob("../input01/*.mpl", recursive=True))

@pytest.mark.timeout(10)
@pytest.mark.parametrize(("mpl_file"), test_data)
def test_run(mpl_file):
    """準備したテストケースを全て実行する．"""
    if not Path(TEST_RESULT_DIR).exists():
        os.mkdir(TEST_RESULT_DIR)
    out_file = Path(TEST_RESULT_DIR).joinpath(Path(mpl_file).stem + ".out")
    res = common_task(mpl_file, out_file)
    if res == 0:
        expect_file = Path(TEST_EXPECT_DIR).joinpath(Path(mpl_file).stem + ".stdout")
        with open(out_file, encoding='utf-8') as ofp, open(expect_file, encoding='utf-8') as efp:
            out_cont = ofp.read().splitlines()
            est_cont = efp.read().splitlines()
            for out_line, est_line in itertools.zip_longest(out_cont, est_cont, fillvalue=""):
                assert out_line == est_line, "Line does not match."
    else:
        with open(out_file, encoding='utf-8') as ofp:
            assert not ofp.read() == '', "Error message should appear."

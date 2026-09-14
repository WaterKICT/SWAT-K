"""SWAT-K QGIS 플러그인 ZIP 배포 패키징 스크립트

사용법:
    python build_plugin.py
    python build_plugin.py --output dist/swat_k.zip
"""

import argparse
from pathlib import Path
import sys
import zipfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def get_plugin_version(src_dir: Path) -> str:
    """metadata.txt에서 플러그인 버전 추출"""
    metadata_file = src_dir / "metadata.txt"
    if metadata_file.is_file():
        with open(metadata_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith("version="):
                    return line.strip().split("=", 1)[1].strip()
    return "0.1.0"


def build_plugin(src_dir: str = "src/swat_k", output_path: str = "swat_k.zip") -> Path:
    """QGIS 규격에 맞춰 플러그인 폴더를 zip 파일로 압축합니다."""
    base_dir = Path(__file__).resolve().parent
    src = (base_dir / src_dir).resolve()
    out = (base_dir / output_path).resolve()

    if not src.is_dir():
        print(f"[오류] 플러그인 소스 디렉터리를 찾을 수 없습니다: {src}", file=sys.stderr)
        sys.exit(1)

    metadata_path = src / "metadata.txt"
    if not metadata_path.is_file():
        print(
            f"[오류] QGIS 플러그인 필수 파일(metadata.txt)이 없습니다: {metadata_path}",
            file=sys.stderr,
        )
        sys.exit(1)

    version = get_plugin_version(src)
    print("=" * 60)
    print(f" SWAT-K QGIS 플러그인 ZIP 패키징 (v{version})")
    print("=" * 60)
    print(f" 소스 경로: {src}")
    print(f" 출력 파일: {out}")
    print("-" * 60)

    out.parent.mkdir(parents=True, exist_ok=True)

    packed_files = []
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(src.rglob("*")):
            # 제외할 불필요한 파일 및 디렉터리 필터링
            if not f.is_file():
                continue
            if "__pycache__" in f.parts:
                continue
            if f.suffix in [".pyc", ".pyo", ".pyd"]:
                continue
            if f.name in [".DS_Store", "Thumbs.db"]:
                continue

            # QGIS 플러그인은 최상위 폴더 이름이 'swat_k' 형태여야 함
            arcname = Path("swat_k") / f.relative_to(src)
            zf.write(f, arcname)
            packed_files.append((arcname, f.stat().st_size))
            print(f"  + {arcname.as_posix():<40} ({f.stat().st_size:>7,} bytes)")

    zip_size = out.stat().st_size
    print("-" * 60)
    print(f"[완료] 총 {len(packed_files)}개 파일 압축 완료 (ZIP 크기: {zip_size:,} bytes)")
    print("\n[안내] QGIS 설치 방법:")
    print("  1. QGIS 실행")
    print("  2. 메뉴: [플러그인] -> [플러그인 관리 및 설치]")
    print("  3. 좌측 탭: [ZIP 파일에서 설치]")
    print(f"  4. 파일 선택: {out}")
    print("  5. [플러그인 설치] 클릭\n")
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SWAT-K QGIS 플러그인 ZIP 빌드 도구")
    parser.add_argument(
        "-o",
        "--output",
        default="swat_k.zip",
        help="생성할 ZIP 파일 경로 (기본값: swat_k.zip)",
    )
    parser.add_argument(
        "-s",
        "--src",
        default="src/swat_k",
        help="플러그인 소스 폴더 경로 (기본값: src/swat_k)",
    )
    args = parser.parse_args()
    build_plugin(src_dir=args.src, output_path=args.output)

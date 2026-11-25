#!/usr/bin/env python3
"""Substitui o firmware principal embutido em TS-2000_V112.exe.

Uso:
    python substituir_firmware.py [EXE] [BIN] [-o SAIDA]

Por omissão:
    EXE   = TS-2000_V112.exe          (nunca é alterado)
    BIN   = TS-2000_V112_main_fw.bin
    SAIDA = TS-2000_V112_mod.exe

O firmware ocupa uma zona fixa do exe (secção .rdata), por isso a
substituição é feita no mesmo sítio e sem mexer no resto do ficheiro.
"""

import argparse
import hashlib
import sys
from pathlib import Path

EXE_SIZE = 413696        # tamanho do TS-2000_V112.exe
FW_OFFSET = 0x174F8      # offset do firmware principal no exe
FW_SIZE = 0x40000        # 262 144 bytes (ROM de 256 KiB)

# SHA-256 do exe sem a zona do firmware: identifica o actualizador V1.12,
# quer tenha o firmware original quer um já substituído.
EXE_SHA256_SEM_FW = "093c3b31d23d3d6632786f8ad2bac6fd28c13b7aa70fd83172dd493acbdd4b2e"

PASTA = Path(__file__).resolve().parent


def sha256(dados: bytes) -> str:
    return hashlib.sha256(dados).hexdigest()


def erro(msg: str) -> "NoReturn":
    sys.exit(f"ERRO: {msg}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Substitui o firmware embutido em TS-2000_V112.exe.")
    ap.add_argument("exe", nargs="?", type=Path, default=PASTA / "TS-2000_V112.exe",
                    help="actualizador de origem (não é alterado)")
    ap.add_argument("bin", nargs="?", type=Path, default=PASTA / "TS-2000_V112_main_fw.bin",
                    help="firmware a inserir (262144 bytes)")
    ap.add_argument("-o", "--saida", type=Path, default=None,
                    help="exe a criar (por omissão TS-2000_V112_mod.exe junto ao exe de origem)")
    ap.add_argument("-f", "--forcar", action="store_true",
                    help="aceitar um exe cujo conteúdo fora do firmware não é o esperado")
    args = ap.parse_args()

    saida = args.saida or args.exe.with_name("TS-2000_V112_mod.exe")

    for p in (args.exe, args.bin):
        if not p.is_file():
            erro(f"ficheiro não encontrado: {p}")
    if saida.resolve() == args.exe.resolve():
        erro("a saída não pode ser o próprio exe de origem.")

    exe = args.exe.read_bytes()
    fw = args.bin.read_bytes()

    if len(fw) != FW_SIZE:
        erro(f"{args.bin.name} tem {len(fw)} bytes; têm de ser exactamente {FW_SIZE}.")
    if len(exe) != EXE_SIZE:
        erro(f"{args.exe.name} tem {len(exe)} bytes; esperava {EXE_SIZE}.")

    fim = FW_OFFSET + FW_SIZE
    if sha256(exe[:FW_OFFSET] + exe[fim:]) != EXE_SHA256_SEM_FW:
        if not args.forcar:
            erro(f"{args.exe.name} não é o actualizador TS-2000 V1.12 esperado "
                 "(o conteúdo fora da zona do firmware é diferente). Use --forcar para ignorar.")
        print("AVISO: exe diferente do esperado; a continuar por causa de --forcar.")

    antigo = exe[FW_OFFSET:fim]
    diferentes = sum(a != b for a, b in zip(antigo, fw))
    novo = exe[:FW_OFFSET] + fw + exe[fim:]
    assert len(novo) == EXE_SIZE

    saida.write_bytes(novo)
    if saida.read_bytes() != novo:
        erro(f"a verificação de {saida} depois da escrita falhou.")

    print(f"Origem   : {args.exe}")
    print(f"Firmware : {args.bin}")
    print(f"Zona     : 0x{FW_OFFSET:X}-0x{fim:X} ({FW_SIZE} bytes)")
    print(f"Bytes alterados em relação ao firmware que estava no exe: {diferentes}")
    if diferentes == 0:
        print("  (o .bin é igual ao firmware já embutido; a saída é uma cópia do exe)")
    print(f"SHA-256 firmware antigo: {sha256(antigo)}")
    print(f"SHA-256 firmware novo  : {sha256(fw)}")
    print(f"Criado   : {saida}")
    print(f"SHA-256  : {sha256(novo)}")


if __name__ == "__main__":
    main()

# TS-2000 V1.12 — limites de banda em `TS-2000_V112_main_fw.bin`

Análise estática de `extracted\TS-2000_V112_main_fw.bin` (262 144 bytes, H8S modo avançado, base 0, logo offset do ficheiro = endereço).
Todas as frequências são inteiros de 32 bits big-endian, em Hz.

Cada entrada está marcada como:

- **[código]** — confirmado pelo desmontado da função indicada;
- **[dados]** — lido da tabela, mas sem referência directa encontrada no código (significado inferido);
- **[manual]** — confirmado pelo service manual do TS-2000/X (`KENWOOD--TS-2000X-Service-Manual.pdf`).

> **Revisão de 25/11/2026.** Documento revisto contra o desmontado actual e o service manual.
> Correcções principais: secção 2.5 (não é um limite: é o ganho de TX dos 1,2 GHz), secções 2.6/2.7 (são os segmentos da configuração de frequência do sintetizador), identificação dos dispositivos em `0x200000`/`0x400000` (DSP TMS320VC5402) e do byte em `0x800002` (entradas "Type setting" do IC19).
> As funções `FUN_xxxxxx` passaram a ser referidas pelo nome actual no IDA. O original está em `LIMITES_BANDAS.md.bak`.

## 1. Como o firmware usa as tabelas

### Primitiva de pesquisa — `band_index_from_freq` @ `0x022364` [código]

Recebe um ponteiro para a frequência e um ponteiro para uma tabela de limites terminada por `0`.
Percorre a tabela e devolve quantos limites são `<=` à frequência (comparação sem sinal, inclusiva).

Os valores terminados em `…001` (1 705 001, 30 000 001, 49 000 001, 60 000 001) resultam desta comparação inclusiva: o limite só é contado a partir de 1 Hz acima do valor redondo.

### Pares inferior/superior [código]

Os limites vêm em pares de tabelas: uma com os limites inferiores e outra com os superiores.
`tx_inhibit_decision` @ `0x02DC8C` calcula o índice em ambas e só não inibe a emissão quando `índice_superior == índice_inferior − 1`, ou seja, quando a frequência está dentro de um dos segmentos.

### Ponteiros em RAM [código]

`select_market_limits` @ `0x01AC0E` instala os ponteiros das tabelas activas (é chamada no arranque por `init_market_and_band_tables` @ `0x01A5A4`):

| RAM | Conteúdo | Valor por omissão | Lido por |
|---|---|---|---|
| `0xFFB4C6` | limites inferiores de TX (principal) | `0x03B254` (ROM) | `tx_inhibit_decision`, `rpt_offset_calc` (`0x0255A6`) |
| `0xFFB4CA` | limites superiores de TX (principal) | `0x03B26C` (ROM) | `tx_inhibit_decision`, `load_edge_tables_from_ext` |
| `0xFFB4BE` | limites de RX (principal) | `0xFFDCCA` (RAM) | `band_edge_lookup`, `clamp_freq_to_band`, `freq_in_tx_segment`, `band_edges_main_sub` |
| `0xFFB4C2` | limites de RX (sub) | `0xFFDD36` (RAM) | `band_edge_lookup`, `freq_in_tx_segment`, `band_edges_main_sub` |
| `0xFFB49E` | 30 000 Hz | constante | sem leitores directos encontrados |
| `0xFFB4A2` | 60 000 000 Hz | constante | sem leitores directos encontrados |

A função lê depois um byte em `0x800002` (guardado em `0xFFDCB5`) e escolhe a variante pelo nibble baixo.
Os bits 6 e 5 desse byte decidem se a variante substitui, respectivamente, as tabelas de TX e as de RX.

| Nibble | Função (nome no IDA) | Tabelas de TX (se bit 6) | Tabelas de RX (se bit 5) | Mercado (inferido, ver secção 4) |
|---|---|---|---|---|
| 4 | `0x01AD30` `set_limits_variant_4` | `0xFFDE62` / `0xFFDE9A` | — | não identificado |
| C | `0x01AD4C` `set_limits_variant_C` | `0xFFDE62` / `0xFFDE9A` | — | não identificado |
| 2 | `0x01AD64` `set_limits_variant_2` | `0xFFDED2` / `0xFFDF0A` | `0xFFDCEE` / `0xFFDD4A` | tipo E |
| 1 | `0x01ADA2` `set_limits_variant_1` | `0xFFDF42` / `0xFFDF7A` | `0xFFDCEE` / `0xFFDD4A` | tipo E |
| A | `0x01ADE0` `set_limits_variant_A` | `0xFFDFB2` / `0xFFDFEA` | `0xFFDCEE` / `0xFFDD4A` | tipo E |
| 6 | `0x01AE1E` `set_limits_variant_6` | `0xFFE022` / `0xFFE05A` | `0xFFDCEE` / `0xFFDD4A` | tipo E |
| 9 | `0x01AE5C` `set_limits_variant_9` | `0xFFE092` / `0xFFE0CA` | `0xFFDD12` / `0xFFDD5E` | tipo E |
| 8 | `0x01AEEE` `set_limits_variant_8` | `0xFFDDEA` / `0xFFDE26` | — | tipo K |
| outro (inclui 0) | `0x01AEBA` `set_limits_variant_default` | `0xFFDD72` / `0xFFDDAE` | — | tipo K |

O byte em `0x800002` é o da configuração de mercado da placa [código + manual].
O service manual (SEMICONDUCTOR DATA, Control unit) lista dois latches de entrada TC74VHC573: o IC20 (SPS, PKSI, S9600, PMUTE, 12OP, CTS3, STA, CON) e o IC19, cujas oito entradas se chamam **SIM0…SIM7, "Type setting 0–7"**.
O firmware lê o IC20 em `0x800001` (o bit 4 é o 12OP, usado por `unit_1g2_detect`), por isso `0x800002` é o IC19: os bits 0–3 (nibble), 5 e 6 deste byte são as entradas SIM0–SIM3, SIM5 e SIM6.
O manual dá os nomes das entradas, mas não a tabela que associa cada combinação a um mercado.
Com o bit 6 a zero o TX fica com a tabela por omissão da ROM (secção 2.1), seja qual for o nibble.

Nota: alguns comentários já existentes no projecto Ghidra não batem com o código (por exemplo, o nibble 2 usa `0xFFDED2`/`0xFFDF0A`, não `0xFFDF42`/`0xFFDF7A`). A tabela acima segue o desmontado.

### As tabelas em RAM não vêm deste ficheiro [código]

`load_edge_tables_from_ext` @ `0x019B30` preenche 38 tabelas em RAM (`0xFFDCCA` … `0xFFE422`) chamando `read_ext_table32`.
Esta lê palavras de 16 bits de um dispositivo externo mapeado em `0x400000` (registo de endereço em `+4/+5`, dados em `+E/+F`), nos endereços de palavra `0x3600` a `0x39xx`, duas palavras por frequência.

Consequência: **os limites por variante de mercado que o rádio aplica não estão em `main_fw.bin`**; estão na memória desse dispositivo externo. O `.bin` contém apenas as tabelas da secção 2.

Há dois dispositivos destes, em `0x200000` e `0x400000`, com os mesmos registos (`+0/+1` controlo, `+4/+5` endereço, `+6/+7` escrita, `+E/+F` leitura).
São os dois DSP [código + manual]:
- o service manual dá o DSP1 (IC516, AF) e o DSP2 (IC515, FI), ambos **TMS320VC5402**, ligados ao CPU principal, cada um com a sua Flash **29LV800B** (IC508 e IC504) "for program and coefficient storage";
- no firmware, o reset destes dispositivos é o pino DRES (PE2), usado por `dsp_wait_ready` @ `0x018EF0`;
- os actualizadores `dsp_upd_reg*` escrevem nos registos do dispositivo em `0x200000` valores de menus que o manual de instruções atribui ao DSP (por exemplo o menu 22, "DSP TX filter bandwidth", vai para o registo `0x85`).

`dsp_wait_ready` espera que arranquem e verifica palavras de identificação (palavra `0x63` = `0x3120`).
O formato dos registos (endereço em `+4/+5`, dados em `+E/+F`) é compatível com a porta de host (HPI) do TMS320VC5402.

O firmware nunca escreve as tabelas de limites nesses dispositivos; só as lê.
Como a única memória não volátil dos DSP é a sua Flash, os limites por mercado vêm, muito provavelmente, dos dados que o DSP carrega da Flash 29LV800B: não do `main_fw.bin`, nem da EEPROM do CPU principal [inferência].
Não está determinado qual dos dois DSP está em `0x400000`.

Os valores próprios de cada mercado segundo o manual (148 MHz como limite, 1,81 MHz, 3,8 MHz, 7,1 MHz) não existem em `main_fw.bin`: foram procurados como 32 bits big-endian, little-endian e com as palavras de 16 bits trocadas.

Depois da carga, para os nibbles 1, 2, A, 6 e 9, `load_edge_tables_from_ext` força a 7 200 000 Hz a terceira entrada da tabela de limites superiores de TX activa.

`load_band_plan` @ `0x003E52` usa as oito primeiras entradas do bloco de RX escolhido (`0xFFDCCA`, `0xFFDCEE` ou `0xFFDD12`) como pares início / (fim − 1) das quatro gamas do plano de bandas.

## 2. Tabelas presentes na ROM

### 2.1 Limites de TX por omissão — `0x03B254` / `0x03B26C` [código]

Instaladas por `select_market_limits` antes da escolha de variante.

| Segmento | Inferior (`0x03B254`) | Superior (`0x03B26C`) |
|---|---|---|
| 1 | 1 705 001 | 30 000 001 |
| 2 | 49 000 001 | 54 000 000 |
| 3 | 142 000 000 | 152 000 000 |
| 4 | 420 000 000 | 450 000 000 |
| 5 | 1 240 000 000 | 1 300 000 000 |

### 2.2 Bandas de amador — `0x03B1E4` / `0x03B21C` [dados]

Treze pares, terminados por `0`. Sem referência directa no código; têm o mesmo formato (14 longs) das tabelas de TX carregadas para RAM.
A entrada dos 2 m é a [10]: `0x03B20C` (144 MHz) e `0x03B244` (146 MHz).
Esta tabela não corresponde por inteiro a nenhum mercado do manual: 2 m e 70 cm são os dos tipos E, 80 m, 40 m e 6 m são os do tipo K, e 23 cm começa em 1260 MHz em vez de 1240 MHz.

| Banda | Inferior (`0x03B1E4`) | Superior (`0x03B21C`) |
|---|---|---|
| 160 m | 1 800 000 | 2 000 000 |
| 80 m | 3 500 000 | 4 000 000 |
| 40 m | 7 000 000 | 7 300 000 |
| 30 m | 10 100 000 | 10 150 000 |
| 20 m | 14 000 000 | 14 350 000 |
| 17 m | 18 068 000 | 18 168 000 |
| 15 m | 21 000 000 | 21 450 000 |
| 12 m | 24 890 000 | 24 990 000 |
| 10 m | 28 000 000 | 29 700 000 |
| 6 m | 50 000 000 | 54 000 000 |
| 2 m | 144 000 000 | 146 000 000 |
| 70 cm | 430 000 000 | 440 000 000 |
| 23 cm | 1 260 000 000 | 1 300 000 000 |

### 2.3 Outros pares de cinco segmentos [dados]

Mesma estrutura de 2.1, sem referência directa encontrada.

| Par | Seg. 1 | Seg. 2 | Seg. 3 | Seg. 4 | Seg. 5 |
|---|---|---|---|---|---|
| `0x03B1B4` / `0x03B1CC` | 1 705 001 – 30 000 001 | 49 000 001 – 54 000 000 | 118 000 000 – 174 000 000 | 420 000 000 – 450 000 000 | 1 240 000 000 – 1 300 000 000 |
| `0x03B284` / `0x03B29C` | 1 705 001 – 30 000 001 | 49 000 001 – 54 000 000 | 144 000 000 – 146 000 000 | 430 000 000 – 440 000 000 | 1 260 000 000 – 1 300 000 000 |

O primeiro par parece cobertura geral de recepção (já rotulado `rx_coverage_a/b` no projecto); o segundo, uma versão restrita às bandas de amador em VHF/UHF.
No segundo par a entrada dos 2 m é a [2]: `0x03B28C` (144 MHz) e `0x03B2A4` (146 MHz).

### 2.4 Tabela `0x03B13E` [dados]

`30 000`, `60 000 001`, `144 000 000`, `146 000 000`, `430 000 000`, `440 000 000`, `1 260 000 000`, `1 300 000 000`, `0`.
Limites alternados início/fim: HF+6 m (30 kHz – 60 MHz), 2 m, 70 cm, 23 cm. Sem referência directa encontrada.
Os 2 m estão em `0x03B146` (144 MHz) e `0x03B14A` (146 MHz).
Tem o mesmo formato (9 longs) das tabelas de RX carregadas para RAM e, em VHF e UHF, os valores que o manual dá para a recepção principal dos tipos E.

### 2.5 Tabela `0x03B1A4` — pontos de calibração do ganho de TX em 1,2 GHz [código + manual] (corrigido)

**Não é um limite de banda.** A função que a usa, antes chamada `limit_check_1p2ghz`, chama-se agora `if_dac_tx_band_gain_update` @ `0x02599E`.
Calcula a tensão "TX band gain control voltage", o canal 7/8 do DAC IC14 da unidade de controlo, e grava-a em `0xFFD07F`, marcando o bit 4 de `0xFFDCC8` para `if_dac_regs_flush_dirty`.

Com a frequência de TX em 1,2 GHz e o bit 5 de `0xFFDC83` a zero, a tabela dá o índice do ponto de calibração:

| Fronteira | Índice | Ponto de calibração (id → item de ajuste) |
|---|---|---|
| < 1 250 000 000 | 0 | `0x72` → item 113, "TX gain for 1.2G band 1240.1M" |
| 1 250 000 000 | 1 | `0x73` → item 114, "TX gain for band 1.2G 1270.1M" |
| ≥ 1 290 000 000 | 2/3 | `0x74` → item 115, "TX gain for 1.2G band 1299.9M" |

Com o bit 5 a um, interpola linearmente (`interp_3pt_linear_u8`) entre os mesmos três pontos, a 1240,1, 1270,1 e 1299,9 MHz. São as frequências de ajuste dos itens 113–115.
Os ids de `blk_ffc1a0_item_ptr_by_id` são o número do item do modo de ajuste do service manual mais 1.
Pela mesma lógica, 144 MHz usa o id `0x61` (item 96) e 430 MHz o id `0x6A` (item 105).

### 2.6 Segmentação interna por gama — `classify_freq_segment_main` @ `0x0158F6` [código]

A função testa as quatro tabelas por ordem e guarda o número da gama (0 a 3) e o índice do segmento.
É a segmentação da banda principal: as quatro gamas são as que o manual (página 106) dá à banda principal.
São fronteiras de comutação internas, não limites de emissão.

**Significado [código + manual]:** são os segmentos da configuração de frequência do sintetizador.
O resultado é usado por `synth_ctx_build` / `synth_recalc_task` para escolher a entrada (R1/N1) das tabelas do PLL e do DDS.
As fronteiras de HF, UHF e 1,2 GHz são **exactamente** as gamas das Tabelas 1, 3 e 5 da CIRCUIT DESCRIPTION do service manual:
- HF: 0,03–2, 2–6, … 56–60 MHz;
- UHF: 420–425, … 443,5–448 MHz;
- 1,2 GHz: 1240–1244, … 1298–1300 MHz.

Em VHF, só 142, 147 e 152 MHz coincidem com a Tabela 2; 144, 145,9 e 149,5 MHz são fronteiras adicionais.

| Gama | Tabela | Fronteiras (MHz) |
|---|---|---|
| 0 — HF/6 m | `0x03B2D6` | 2, 6, 9, 13, 17, 18, 22, 24, 25, 26, 30, 33, 37, 41, 45, 49, 52, 56, 60,000001 |
| 1 — VHF | `0x03B326` | 142, 144, 145,9, 147, 149,5, 152 |
| 2 — UHF | `0x03B342` | 420, 425, 431,5, 435,5, 439,5, 443,5, 448, 454, 460 |
| 3 — 1,2 GHz | `0x03B36A` | 1240, 1244, 1246, 1250, 1254, 1256, 1259, 1263, 1267, 1271, 1275, 1278, 1281, 1285, 1289, 1292,5, 1295, 1298, 1300 |

`0x03B2D6` é também usada por `hf_freq_uses_if1_69m085` @ `0x017938`, que decide a 1.ª FI em HF.

### 2.7 Segmentação do segundo caminho — `classify_freq_segment_alt` @ `0x0159F6` [código]

Mesma lógica, com duas gamas. É a segmentação do sub-receptor: 118 – 174 MHz e 220 – 512 MHz são exactamente as gamas que o manual (página 106) dá ao sub-receptor do tipo K.

Na gama 220–512 MHz, as fronteiras (220, 252,5, 290, 329, 400, 446 e 512 MHz) são as da comutação de VCO da Tabela 4 do service manual, a configuração de frequência do sub-receptor [manual].
Por exemplo, 252,5 e 290 MHz são as fronteiras das linhas BSW1/BSW2, e 290 MHz é onde a fórmula muda de N = 2 × (f − 58,525) para N = f + 58,525.
Em 118–174 MHz, a Tabela 4 tem mais fronteiras (118,95 e 154,5 MHz) do que a tabela da ROM.

| Gama | Tabela | Fronteiras (MHz) |
|---|---|---|
| 1 | `0x03B3CA` | 118, 135, 174 |
| 2 | `0x03B3DA` | 220, 252,5, 290, 329, 400, 446, 512 |

### 2.8 Constantes que não são limites de banda

- `0x03B3BA`: 11 150 000, 467 000, 10 583 000 [código + manual]. São as frequências base dos osciladores gerados por DDS AD9835 (secção "Local Signals" do service manual):
  - RX LO3 = 11,150 MHz (IC603) e RCAR = 467 kHz (IC601), lidas por `dds_calc_rx_lo_11m15_467k` @ `0x01721C`;
  - TCAR = 10,583 MHz (IC602), lida por `dds_calc_tx_lo_10m583` @ `0x0172E4`.
- `0x03AF34`: 118, 144, 340, 430 MHz, lidas por `vfo_reset_apply`, seguidas da lista de passos de sintonia (5 kHz … 1 MHz) em `0x03AF44`.
- `0x03B872`, `0x03B8BA`, `0x03B8D8`: tabelas de desvio automático de repetidor (secção 4.2). São as únicas tabelas de frequências da ROM cuja escolha depende do mercado.
- `0x03B7C6`: dez registos de 16 bytes, um por índice de mercado, com os desvios de repetidor por omissão (secção 5).

## 3. Limites codificados como imediatos no código [código]

Comparações `cmp.l` encontradas, sem tabela:

| Valor (Hz) | Funções |
|---|---|
| 30 000 | `freq_round_to_step`, `dial_vfo_freq_apply`, `dxcluster_parse_spot`, `pscan_setup`, `sci3_freq_step_cmd` |
| 522 000 | `freq_step_size_hz`, `multi_ch_vfo_freq_step` (início da banda AM de radiodifusão, passo de 9 kHz) |
| 2 000 000 | `0x0230FA` (sem nome) |
| 30 000 000 / 30 000 001 | `at_lc_dir_from_detectors`, `at300_tune_start_check`, `swr_calc`, `meters_send_to_panel`, `if_filter_select_update`, `rf_switch_word_update`, `main_freq_30mhz_flag_upd`, `smeter_fm_cal_table_for_band` |
| 60 000 000 / 60 000 001 | `at_fen2_lc_shadow_update`, `at_tune_start_check`, `at_rx_inline_get`, `at_tx_inline_get`, `panel_refresh_task`, `meters_send_to_panel`, `tuning_dial_step`, `freq_entry_apply`, `multi_ch_vfo_freq_step`, `freq_to_band_unit_bits`, `pscan_freq_step`, `cat_fa_fb_set_freq` |
| 300 000 000 | `meters_send_to_panel`, `dsp_reg83_mode_nibble`, `freq_to_band_unit_bits`, `tx_power_range_get`, `smeter_fm_cal_table_for_band`, `sql_threshold_calc_sub` |
| 420 000 000 | `rpt_shift_dir_cycle`, `cat_os_set` |
| 1 240 000 000 | `cat_parse_freq_digits`, `call_ch_defaults_write` |

Estes valores separam as gamas HF (< 30 MHz), 6 m (< 60 MHz), VHF (< 300 MHz), UHF e 1,2 GHz.
Pelos nomes das funções, são comutações internas: sintonizador de antena (só abaixo de 30 ou 60 MHz), tabelas do S-meter, filtros, passos de sintonia, desvio de repetidor e validação de frequência por CAT. **Nenhum é um limite de emissão.**

`init_band_memories_default` @ `0x003C40` inicializa as memórias de banda com 9 500 000 Hz (HF), 144 000 000, 430 000 000 e 1 260 000 000 Hz.

## 4. Banda dos 2 m e jumpers de mercado

### 4.1 Limites segundo o manual

Do manual de instruções (`ida\TS-2000_Instruction_manual__Rve2.pdf`, páginas 105 e 106):

| | Tipo K | Tipos E |
|---|---|---|
| TX 160 m | 1,8 – 2,0 MHz | 1,81 – 2,0 MHz (E2: 1,83 – 1,85 MHz) |
| TX 80 m | 3,5 – 4,0 MHz | 3,5 – 3,8 MHz |
| TX 40 m | 7,0 – 7,3 MHz | 7,0 – 7,1 MHz |
| TX 6 m | 50 – 54 MHz | 50 – 52 MHz (E2: 50,0 – 50,2 MHz) |
| TX 2 m | 144 – 148 MHz | 144 – 146 MHz |
| TX 70 cm | 430 – 450 MHz | 430 – 440 MHz |
| TX 23 cm | 1240 – 1300 MHz | 1240 – 1300 MHz |
| RX principal VHF / UHF | 142 – 152 / 420 – 450 MHz | 144 – 146 / 430 – 440 MHz |
| RX sub-receptor | 118 – 174 / 220 – 512 MHz | 144 – 146 / 430 – 440 MHz |

As bandas de 30 m a 10 m são iguais em todos os tipos (valores da secção 2.2).

### 4.2 Que nibble é o tipo K e quais são os tipos E [código + manual]

`market_index_from_straps` @ `0x004BF8` converte o nibble dos jumpers num índice de mercado:
0/outro → 1, 8 → 2, 4 → 3, C → 4, 2 → 5, 1 → 6, A → 7, 6 → 8, 9 → 9.

`select_aro_tables` @ `0x004C46` usa esse índice para escolher o desvio automático de repetidor.
As tabelas têm registos de 6 bytes: frequência (32 bits, Hz), direcção (`00` simplex, `FF` −, `01` +) e `00`; terminam em `FFFFFFFF`.

| Tabela | Conteúdo | Índices (nibbles) |
|---|---|---|
| `0x03B872` | 145,1 −, 145,5 S, 146,0 +, 146,4 S, 146,6 −, 147,0 +, 147,4 S, 147,6 −, 148,0 S | 1, 2, 4 (0/outro, 8, C) |
| `0x03B8BA` | 145,6 −, 145,8 S | 5 a 9 (2, 1, A, 6, 9) |
| `0x03B8D8` | 1,2 GHz: 1282 – 1288 MHz − | 1, 2 (0/outro, 8) |
| nenhuma | — | 3 (4) |

A primeira é igual à que o manual (página 34) dá para o tipo K e a segunda à dos tipos E.
Daqui resulta a coluna "Mercado" da secção 1: nibbles 0/outro e 8 = tipo K; nibbles 2, 1, A, 6 e 9 = tipos E.
A correcção dos 7,2 MHz em `load_edge_tables_from_ext` aplica-se exactamente aos mesmos cinco nibbles, o que é coerente com serem os tipos E (o manual dá-lhes 40 m até 7,1 MHz).
A atribuição é inferida destas duas coisas.
O manual de instruções não traz a lista de jumpers. O service manual só nomeia as entradas (SIM0–SIM7, "Type setting", secção 1) e também não tem a tabela de combinações.
Os nibbles 4 e C não ficaram identificados.

### 4.3 Onde ficam os limites dos 2 m

O mesmo firmware serve todos os mercados e muda de 146 para 148 MHz apenas pelos jumpers.

| Limite | Onde | Marcação |
|---|---|---|
| TX, tipos E | entrada [10] (`+0x28`) das tabelas de TX de 14 entradas: `0xFFDED2`/`0xFFDF0A`, `0xFFDF42`/`0xFFDF7A`, `0xFFDFB2`/`0xFFDFEA`, `0xFFE022`/`0xFFE05A`, `0xFFE092`/`0xFFE0CA` | [dados] posição inferida do formato da secção 2.2 e de a entrada [2] ser os 40 m |
| TX, tipo K | tabelas de 15 entradas `0xFFDD72`/`0xFFDDAE` e `0xFFDDEA`/`0xFFDE26` | posição da entrada dos 2 m não determinada |
| TX com bit 6 a zero | `0x03B25C` (142 MHz) / `0x03B274` (152 MHz), na ROM | [código] |
| RX principal | entradas [2] e [3] de `0xFFDCCA` (por omissão, tipo K), `0xFFDCEE` (tipos E) ou `0xFFDD12` (nibble 9) | [código] `load_band_plan` |
| RX sub-receptor | entradas [0] e [1] de `0xFFDD36` (por omissão, tipo K), `0xFFDD4A` (tipos E) ou `0xFFDD5E` (nibble 9) | [código + manual] secção 4.4 |

Os valores destas tabelas de RAM vêm do dispositivo externo, por isso não foi possível lê-los aqui; os da secção 4.1 são os esperados segundo o manual, não os observados.

As três ocorrências de 144/146 MHz na ROM (secções 2.2, 2.3 e 2.4) não são lidas pelo código: mudar 146 para 148 MHz nelas não deve alterar o comportamento do rádio.
O valor 148 000 000 aparece uma única vez no ficheiro, em `0x03B8A8`, dentro da tabela de desvio automático do tipo K; não é um limite de banda.

O único sítio onde o firmware altera um limite depois de carregado é `0x019DFE` (entrada [2] da tabela superior de TX = 7 200 000 Hz).
Nessa mesma tabela o limite superior dos 2 m seria `@(0x28,er0)`.

### 4.4 Banda principal (main) ou sub-receptor (sub)

Gamas de recepção segundo o manual (página 106):

| | Tipo K | Tipos E |
|---|---|---|
| Principal | 0,03 – 60 MHz; 142 – 152 MHz; 420 – 450 MHz; 1240 – 1300 MHz | 0,03 – 60 MHz; 144 – 146 MHz; 430 – 440 MHz; 1240 – 1300 MHz |
| Sub-receptor | 118 – 174 MHz; 220 – 512 MHz | 144 – 146 MHz; 430 – 440 MHz |

A banda principal tem quatro gamas e o sub-receptor duas. Só a banda principal emite.

No código [código]:

- `0xFFB4BE` aponta para tabelas de 9 longs (4 pares início/fim + `0`) e `0xFFB4C2` para tabelas de 5 longs (2 pares + `0`), o que bate com as quatro e duas gamas do manual.
- `band_edges_main_sub` @ `0x027D08`: com argumento 0 usa `0xFFB4BE` e a frequência apontada por `+0x200` da estrutura em `0xFFB266`, e guarda início/fim em `0xFFB76E` / `0xFFB772`; com argumento ≠ 0 usa `0xFFB4C2` e a frequência apontada por `+0x210`, e guarda em `0xFFB776` / `0xFFB77A`.
- `vfo_reset_apply` @ `0x019266` (reposição do VFO, comando CAT SR1) inicializa a frequência apontada por `+0x200` com 14 000 000 Hz e a apontada por `+0x210` com 144 000 000 Hz, ou seja, uma banda principal em HF e um sub-receptor em VHF.
- `tx_inhibit_decision` usa a frequência apontada por `+0x204` (TX da banda principal) com as tabelas de `0xFFB4C6` / `0xFFB4CA`.

Classificação das tabelas:

| Banda | Tabelas | Fundamento |
|---|---|---|
| Principal | RAM `0xFFDCCA`, `0xFFDCEE`, `0xFFDD12` (RX; 2 m nas entradas [2]/[3]) | [código] instaladas em `0xFFB4BE` |
| Sub-receptor | RAM `0xFFDD36`, `0xFFDD4A`, `0xFFDD5E` (RX; 2 m nas entradas [0]/[1]) | [código] instaladas em `0xFFB4C2` |
| Principal | todas as tabelas de TX em RAM (`0xFFDD72` … `0xFFE0CA`) e a de omissão na ROM (2.1) | [código] só a banda principal emite |
| Principal | 2.2 e segundo par de 2.3 (formato de TX), 2.4 (formato de RX principal, 4 gamas) | [dados] pelo formato |
| Principal | 2.5 (1,2 GHz) e 2.6 (`classify_freq_segment_main`) | [código + manual] gamas da banda principal |
| Sub-receptor | 2.7 (`classify_freq_segment_alt`): `0x03B3CA`, `0x03B3DA` | [código + manual] gamas do sub-receptor do tipo K |
| Indeterminado | primeiro par de 2.3 (`0x03B1B4` / `0x03B1CC`) | mistura 118 – 174 MHz (sub-receptor) com 420 – 450 e 1240 – 1300 MHz (principal) |

Que a primeira gama do sub-receptor é a de VHF (2 m) resulta da ordem crescente das tabelas e das duas gamas do manual; os valores em si vêm do dispositivo externo e não foram lidos.

### 4.5 Marcação no IDA

Tudo isto está marcado na base de dados do IDA; o resumo está em `ida\tabela.txt`.
Os comentários das tabelas começam por `[MAIN]` ou `[SUB]`; os ponteiros chamam-se `p_rx_edges_main`, `p_rx_edges_sub`, `p_tx_lower_main` e `p_tx_upper_main`.

## 5. Desvios de repetidor (repeater offset)

### 5.1 Desvios por omissão — `market_records` @ `0x03B7C6` [código + manual]

Dez registos de 16 bytes, indexados pelo índice de mercado de `market_index_from_straps` (secção 4.2).

| Offset no registo | Conteúdo |
|---|---|
| `+0` | bits que activam o desvio automático por banda (`aro_band_enabled` @ `0x004A4E`) |
| `+2` … `+14` | sete palavras de desvio, em unidades de 50 kHz |

`offset_slot_for_band` @ `0x004AD0` escolhe a palavra: banda principal HF, 50, 144, 430 MHz e 1,2 GHz → palavras 0, 1, 3, 5 e 6; as quatro bandas do sub-receptor → palavras 2, 3, 4 e 5.
As palavras de 144 MHz (`+8`) e de 430 MHz (`+12`) servem portanto a banda principal e o sub-receptor.

| Banda | Tipo K | Tipos E | Endereços |
|---|---|---|---|
| 144 MHz (`+8`) | `0x000C` = 600 kHz | `0x000C` = 600 kHz | K: `0x03B7DE`, `0x03B7EE`; E: `0x03B81E`, `0x03B82E`, `0x03B83E`, `0x03B84E`, `0x03B85E` |
| 430 MHz (`+12`) | `0x0064` = 5,0 MHz | `0x0020` = 1,6 MHz | K: `0x03B7E2`, `0x03B7F2`; E: `0x03B822`, `0x03B832`, `0x03B842`, `0x03B852`, `0x03B862` |
| 1,2 GHz (`+14`) | `0x00F0` = 12,0 MHz | `0x02BC` = 35,0 MHz | K: `0x03B7E4`, `0x03B7F4`; E: `0x03B824`, `0x03B834`, `0x03B844`, `0x03B854`, `0x03B864` |

São exactamente os valores por omissão do manual (página 32); em 29 e 50 MHz a palavra é 0 (simplex), também como no manual.
Os registos dos nibbles 4 e C têm os mesmos desvios do tipo K.

`load_default_repeater_offsets` @ `0x0049E0` copia estas palavras para RAM (`0xFFB266+0x80` para a banda principal, `+0x8A` para o sub-receptor).
É chamada por `master_reset_apply` @ `0x018260`, a reposição total (comando CAT SR2, ou A=B + POWER), que apaga a EEPROM e repõe os valores de fábrica [código].
A conversão para Hz multiplica a palavra por 50 000 (constante em `0x03B5A2`, em `rpt_offset_calc` @ `0x0255A6`).

### 5.2 Desvios fixos dos tipos E [código]

Na direcção `=` dos tipos E o desvio não vem da tabela: `rpt_offset_calc` usa imediatos, 7 600 000 Hz em `0x025788` (430 MHz) e 6 000 000 Hz em `0x025790` (1,2 GHz), com sentido negativo.
Batem com os −7,6 MHz e −6,0 MHz do manual.

### 5.3 Direcção automática

As tabelas que escolhem automaticamente o sentido do desvio são as da secção 4.2 (`0x03B872`, `0x03B8BA`, `0x03B8D8`).
Não há tabela de direcção automática para 430 MHz.

## 6. O que ficou por confirmar

- O conteúdo das 38 tabelas em RAM (secção 1) vem do DSP em `0x400000`, muito provavelmente dos dados da sua Flash 29LV800B, que não faz parte deste ficheiro. Para ler os valores reais é preciso a imagem dessa Flash ou ler a memória do DSP no rádio.
- ~~Que os dispositivos em `0x200000` e `0x400000` são os DSP é inferência~~ — **confirmado** (secção 1): são os DSP TMS320VC5402. Falta saber qual dos dois (DSP1 de AF ou DSP2 de FI) está em `0x400000`.
- As tabelas 2.2, 2.3 e 2.4 não têm nenhuma referência no código (nem ponteiro, nem imediato, em todo o ficheiro); tudo indica que não são usadas. Verificado de novo: não há nenhum ponteiro de 32 bits para elas na ROM.
- A atribuição dos nibbles a mercados (secção 4.2) é inferida. O service manual confirma que o byte em `0x800002` são as entradas "Type setting" SIM0–SIM7 do IC19, mas não traz a tabela de combinações nem diz que jumper físico corresponde a cada bit.
- Os nibbles 4 e C não estão associados a nenhum mercado.
- Nas tabelas de TX do tipo K (15 entradas) não se sabe qual é a entrada dos 2 m.

# Attribution — intent-clarify

本 skill (`$intent-clarify`) の core mechanism は **addyosmani/agent-skills** (MIT License, Copyright (c) 2025 Addy Osmani) の以下 2 skill から抽出 + 日本語訳 + ハーネス統合のため構造化変更したもの。

## 抽出元

### `interview-me` から抽出

- hypothesis + confidence (= SKILL.md Step 2-1)
- 1 質問 + GUESS の形式 (= Step 2-2)
- want vs should-want 検知 (= Step 2-3)
- 6 軸 restate (= Step 3-1)
- 明示 yes 確認 (= Step 3-2)
- 「次 3 質問予測可能」 stop 条件 (= Exit criterion)

### `idea-refine` から抽出

- Out of scope を必須 1 軸として 6 軸に組み込み (= Step 3-1)
- 「Not Doing list の表面化」 概念

## 統合のため追加した点

- 既存 5 subagent 召集パターン (= architect / fullstack-engineer / reviewer / qa-verifier / docs-curator、 Phase 1)
- task-routing への one-directional hand-off 統合 (= Phase 4 / Final Report、 ループしない設計)
- 日本語 user 用の検知パターン (= Step 2-3 / Step 3-2、 「ちゃんとした」 「お任せします」 等)
- Exit criterion の operationalize 手順 (= 想定 reply 書き出しによる vibe gate 回避)
- 6 軸の forcing function YAML スキーマ化 (= memory [[harness-3-layer-design]] 連携)
- hand-off payload の confidence_carry_over + fragility_warnings (= task-routing 受け取り contract)
- PII guard セクション (= user 発話保護)

## License

addyosmani/agent-skills は MIT License。 本 skill も派生として MIT 互換で配布。

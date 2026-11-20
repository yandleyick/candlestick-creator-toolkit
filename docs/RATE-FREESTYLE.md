# Rate Freestyle

Created by **Candlestick (yandleyick)**. Give the plugin two performances or timestamped transcripts and it compares the writing passage by passage. The default score weights complexity at 30%, depth at 30%, and connected development at 40%. Connected development rewards a later line that builds on an earlier one through a callback, reversal, or payoff.

[Download the plugin ZIP](https://raw.githubusercontent.com/yandleyick/candlestick-creator-toolkit/main/downloads/rate-freestyle-plugin.zip) · [Read the scoring rubric](../plugins/rate-freestyle-plugin/skills/rate-freestyle/references/rubric.md) · [Browse the plugin source](../plugins/rate-freestyle-plugin)

## Install in Codex

```shell
codex plugin marketplace add yandleyick/candlestick-creator-toolkit
codex plugin add rate-freestyle-plugin@candlestick-creator-toolkit
```

## Try it

Attach two excerpts from the [freestyle editor](FREESTYLE.md), or paste timestamped transcripts with performer labels. Then ask:

> Use Rate Freestyle to compare these two verses. Score complexity, depth, and connected development. For each verse, give the timestamp of the strongest setup and payoff and explain how the payoff changes the meaning of the setup.

The plugin can analyze the writing from a transcript. For feedback on flow, timing, or breath control, supply audio the reviewer can hear.

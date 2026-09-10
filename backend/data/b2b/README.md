# B2B sales win/loss sample

`sales_win_loss.csv` is the public IBM Watson Sales Win/Loss sample. It contains
78,025 closed B2B opportunities from one reporting period. The repository uses
the public mirror below as its versioned source.

- Public mirror: <https://github.com/vkrit/data-science-class/blob/master/WA_Fn-UseC_-Sales-Win-Loss.csv>
- SHA-256: `31afdb83aa46b54f62f5cdbfe1ccf00f395266254a0249c96ceef8522cc12b24`
- Rows: 78,025 before removing 55 exact duplicates
- Outcome: `Opportunity Result` (`Won` or `Loss`)

The mirror does not state an explicit data license. Verify redistribution rights
before using this sample outside an educational or portfolio context. The
training metadata records the exact checksum so a different source cannot be
silently substituted.

## Leakage policy

Only product/category, region, route to market, opportunity amount, client-size
bands, prior-client-revenue band, and known/unknown competitor status enter the
model. Sales-cycle duration, stage transition, result, ratio, and derived deal
size fields are excluded because they either reveal the completed sales process
or duplicate another input.

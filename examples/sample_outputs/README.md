# Sample outputs (real, unedited)

One run of `python -m outreach --prospects examples/prospects.csv --product examples/product.md --sender "Alex"` with `LLM_MODEL=ollama/qwen2.5:7b` on 2026-10-20, on a 2-vCPU cloud machine with no GPU. The prospects and the product are fictional.

Result: **2/2 drafts ready, 0 flagged**, both on the first attempt, 2m41s for the batch.

What the guards confirmed for both drafts: subject under 7 words, body under 120 words, the company is named, exactly one question, no template opener, no em dashes, no exclamation points, no banned words, and no number that isn't in the prospect notes or product sheet. Dana's draft reuses her "9 days" close figure correctly.

What a human should still fix before sending (the guards can't see these):

- **Dana Whitfield:** "Could I share more details on how we've helped other companies..." implies customer stories the product sheet doesn't contain. The prompt says never to invent customers, and the model hinted at them anyway without naming any.
- **Marcus Oyelaran:** the notes say Tidewater opened 3 new clinic locations, but the draft says the company is "focused on streamlining operations across multiple locations". That's vaguer than the fact it was given, and "Have you considered this solution?" is a weak ask.

That's the intended split: code blocks the failures that can be checked (invented numbers, length, missing ask), and a rep reviews tone and claims before anything is sent. Nothing is ever sent automatically.

**Update 2026-10-21:** a guard added in the audit now catches the Dana problem above (implied customer proof the product sheet doesn't back up), so under the current checks her draft would be sent back for a retry rather than marked ready. The files here are left as the original run produced them.

# CRM-063 — Argentine customer phone matching

Status: Approved

## Scope

- The shared identity resolver recognizes equivalent Argentine numbers in Web and
  WhatsApp intake, manual opportunity creation, and customer import. Compare complete
  numbers by national number, including the area code. Accept domestic and international
  dialing prefixes and compare older saved values without rewriting them.
- A local mobile number with the `15` prefix can match the subscriber number of a
  complete Argentine number. If multiple customer records match, keep the existing
  ambiguity handling. Complete numbers with different area codes remain distinct.
- Keep exact normalized email matching. An email match and a phone match pointing to
  different customers are treated as ambiguous by the existing resolver.
- Case creation after a WhatsApp opportunity closes, message routing, retroactive
  customer merges, and contact field edits are outside this change.

## Acceptance criteria

- AC-01: All six formats supplied for the Tandil example match one existing customer
  in either direction, including with the international mobile prefix from WhatsApp.
- AC-02: A local mobile number shared by multiple area codes requires review; sending a
  complete number retains the area code. Local numbers match the entire subscriber part.
- AC-03: Exact email continues to reuse a unique customer when phone gives no match.
  An email and a phone identifying different customers require review.
- AC-04: Concurrent lead intakes with equivalent phone formats create one customer.
  CSV preview detects equivalent phones within a file while retaining distinct full
  numbers. Existing customer and intake values stay as entered.

## Open decisions

None.

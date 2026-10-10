# Design

The user wants a quickly understandable system diagram, not another dense architecture document. Use an original clean systems-infographic treatment: white canvas, simple outlined components, numbered arrows, restrained green/amber/gray status colors and short English labels. This follows their earlier English-artifact preference and avoids the previous clipped diagram labels.

The diagram has three explicitly separate lanes: the working local case-storage/export path; implemented but disconnected browser/model/runtime/evaluation components; and missing production connections. Solid arrows describe only installed paths. No line from the pending outbox to a model implies a working worker. Source commit is `3d08cd3`; previous verification receipts are labelled historical, not rerun.

Save a lightweight SVG source and PNG preview in `docs/architecture/`. Verify XML, required status labels, SVG text bounds in Chromium and raster appearance. No image-generation service is needed for precise code-native diagram geometry.

Initial cloud preflight was read-only and failed with `invalid_grant`, leaving inventory unknown. After the user confirmed `genaide/europe-west2`, £200/month and completed login, fresh inventory succeeded. The user-authorized private case-only provisioning follows a separately reviewed cloud profile. Update the diagram only from observed live acceptance, preserving the distinction between case storage and disconnected product components. Existing unsupported model/runtime safety guards stay intact.

The user's standing autonomous/parallel instruction waives repeated internal document approval gates; it does not authorize choosing unbounded cloud cost or bypassing the blocked production guard.

# Negative branches for public cases 001–050

Each case: snapshot at escalation, the recorded next action, and 4–6 alternative continuations (a new event inserted after a recorded one) with the decision the coordinator should take. JSON is the source; the .md files are rendered from it by `_spec/negatives_tool.py`.

| Case | Title | Branches | Failure modes |
|---|---|---|---|
| [001](001.md) | Recipient cannot attend the scheduled delivery window | 5 | AMBIGUOUS_REPLY, STALE_STATE, CHANNEL_FAILURE, UNAUTHORISED_REPLY, CUSTOMER_CANCELS |
| [002](002.md) | Apartment number missing from the delivery address | 5 | SNAPSHOT_CONFLICT, AMBIGUOUS_REPLY, NO_REPLY, CHANNEL_FAILURE, CONFLICTING_RECORDS |
| [003](003.md) | Driver cannot access a gated residential building | 6 | NO_REPLY, OUT_OF_POLICY_ASK, UNAUTHORISED_REPLY, STALE_STATE, CONFLICTING_RECORDS, PHYSICAL_FAILURE |
| [004](004.md) | Recipient requests a call shortly before arrival | 6 | SNAPSHOT_CONFLICT, CHANNEL_FAILURE, STALE_STATE, OUT_OF_POLICY_ASK, UNAUTHORISED_REPLY, CONFLICTING_RECORDS |
| [005](005.md) | Recipient asks for an authorised household member to receive the parcel | 6 | SNAPSHOT_CONFLICT, AMBIGUOUS_REPLY, STALE_STATE, CHANNEL_FAILURE, UNAUTHORISED_REPLY, OUT_OF_POLICY_ASK |
| [006](006.md) | Customer requests collection from a staffed pickup point | 6 | STALE_STATE, CHANNEL_FAILURE, DUPLICATE_REQUEST, CUSTOMER_CANCELS, CONFLICTING_RECORDS, UNAUTHORISED_REPLY |
| [007](007.md) | Pickup deadline is too short for the recipient | 6 | STALE_STATE, NO_REPLY, UNAUTHORISED_REPLY, CUSTOMER_CANCELS, CONFLICTING_RECORDS, OUT_OF_POLICY_ASK |
| [008](008.md) | Recipient needs a defined delivery slot rather than an all-day estimate | 5 | AMBIGUOUS_REPLY, STALE_STATE, CHANNEL_FAILURE, UNAUTHORISED_REPLY, NO_REPLY |
| [009](009.md) | Bulky delivery requires the recipient to clear an access route | 6 | AMBIGUOUS_REPLY, OUT_OF_POLICY_ASK, NO_REPLY, NEEDS_HUMAN, CONFLICTING_RECORDS, STALE_STATE |
| [010](010.md) | Recipient wants delivery held during a short absence | 6 | SNAPSHOT_CONFLICT, CHANNEL_FAILURE, STALE_STATE, UNAUTHORISED_REPLY, CUSTOMER_CANCELS, CONFLICTING_RECORDS |
| [011](011.md) | Shipment tracking has not updated after depot arrival | 6 | CHANNEL_FAILURE, NO_REPLY, PHYSICAL_FAILURE, DUPLICATE_REQUEST, UNAUTHORISED_REPLY, CONFLICTING_RECORDS |
| [012](012.md) | Promised delivery day missed after vehicle breakdown | 6 | CHANNEL_FAILURE, STALE_STATE, NO_REPLY, CUSTOMER_CANCELS, AMBIGUOUS_REPLY, CONFLICTING_RECORDS |
| [013](013.md) | Recipient disputes a recorded failed delivery attempt | 5 | CONFLICTING_RECORDS, CHANNEL_FAILURE, STALE_STATE, NEEDS_HUMAN, DUPLICATE_REQUEST |
| [014](014.md) | Driver arrives after the business receiving desk closes | 5 | UNAUTHORISED_REPLY, AMBIGUOUS_REPLY, NO_REPLY, OUT_OF_POLICY_ASK, STALE_STATE |
| [015](015.md) | Parcel has been routed to the wrong local depot | 5 | CHANNEL_FAILURE, CONFLICTING_RECORDS, DUPLICATE_REQUEST, CUSTOMER_CANCELS, PHYSICAL_FAILURE |
| [016](016.md) | Pickup locker is full | 5 | UNAUTHORISED_REPLY, AMBIGUOUS_REPLY, CHANNEL_FAILURE, STALE_STATE, CONFLICTING_RECORDS |
| [017](017.md) | Delivery notification contains an unusable tracking link | 5 | SNAPSHOT_CONFLICT, UNAUTHORISED_REPLY, CHANNEL_FAILURE, DUPLICATE_REQUEST, CONFLICTING_RECORDS |
| [018](018.md) | Shipment is approaching its return-to-sender deadline | 6 | NO_REPLY, UNAUTHORISED_REPLY, AMBIGUOUS_REPLY, STALE_STATE, CHANNEL_FAILURE, CUSTOMER_CANCELS |
| [019](019.md) | Severe weather suspends the delivery route | 5 | CONFLICTING_RECORDS, UNAUTHORISED_REPLY, OUT_OF_POLICY_ASK, NEEDS_HUMAN, STALE_STATE |
| [020](020.md) | A multi-parcel order arrives with one parcel still outstanding | 5 | DUPLICATE_REQUEST, STALE_STATE, CONFLICTING_RECORDS, PHYSICAL_FAILURE, CUSTOMER_CANCELS |
| [021](021.md) | Outer packaging is damaged and the merchant needs evidence | 5 | SNAPSHOT_CONFLICT, CHANNEL_FAILURE, OUT_OF_POLICY_ASK, AMBIGUOUS_REPLY, NEEDS_HUMAN |
| [022](022.md) | A delivered household item is confirmed broken | 5 | CHANNEL_FAILURE, UNAUTHORISED_REPLY, STALE_STATE, CONFLICTING_RECORDS, CUSTOMER_CANCELS |
| [023](023.md) | A leaking parcel is reported at the depot | 6 | CHANNEL_FAILURE, UNAUTHORISED_REPLY, NEEDS_HUMAN, NO_REPLY, OUT_OF_POLICY_ASK, CONFLICTING_RECORDS |
| [024](024.md) | Tracking says delivered but the recipient has no parcel | 5 | CHANNEL_FAILURE, OUT_OF_POLICY_ASK, UNAUTHORISED_REPLY, CUSTOMER_CANCELS, CONFLICTING_RECORDS |
| [025](025.md) | Carrier confirms a parcel is lost after investigation | 5 | OUT_OF_POLICY_ASK, UNAUTHORISED_REPLY, STALE_STATE, AMBIGUOUS_REPLY, CONFLICTING_RECORDS |
| [026](026.md) | Parcel was handed to the wrong address and the carrier located it | 5 | UNAUTHORISED_REPLY, OUT_OF_POLICY_ASK, STALE_STATE, PHYSICAL_FAILURE, CONFLICTING_RECORDS |
| [027](027.md) | Customer receives another customer's parcel | 5 | DUPLICATE_REQUEST, OUT_OF_POLICY_ASK, UNAUTHORISED_REPLY, PHYSICAL_FAILURE, CONFLICTING_RECORDS |
| [028](028.md) | Wrong item inside a correctly addressed parcel | 5 | UNAUTHORISED_REPLY, STALE_STATE, NO_REPLY, OUT_OF_POLICY_ASK, CONFLICTING_RECORDS |
| [029](029.md) | Refrigerated food arrives outside the merchant's documented temperature conditions | 5 | NEEDS_HUMAN, OUT_OF_POLICY_ASK, UNAUTHORISED_REPLY, CONFLICTING_RECORDS, NO_REPLY |
| [030](030.md) | A high-value shipment lacks an accessible proof-of-delivery record | 5 | SNAPSHOT_CONFLICT, CHANNEL_FAILURE, OUT_OF_POLICY_ASK, CONFLICTING_RECORDS, UNAUTHORISED_REPLY |
| [031](031.md) | Return approved but the customer has no return label | 6 | CHANNEL_FAILURE, STALE_STATE, UNAUTHORISED_REPLY, CONFLICTING_RECORDS, CUSTOMER_CANCELS, OUT_OF_POLICY_ASK |
| [032](032.md) | Customer cannot print a return label | 6 | CHANNEL_FAILURE, STALE_STATE, UNAUTHORISED_REPLY, CONFLICTING_RECORDS, OUT_OF_POLICY_ASK, DUPLICATE_REQUEST |
| [033](033.md) | Courier misses a booked return collection | 6 | STALE_STATE, CHANNEL_FAILURE, PHYSICAL_FAILURE, CONFLICTING_RECORDS, UNAUTHORISED_REPLY, NO_REPLY |
| [034](034.md) | Returned parcel has reached the carrier depot but not the merchant warehouse | 6 | CONFLICTING_RECORDS, CHANNEL_FAILURE, OUT_OF_POLICY_ASK, UNAUTHORISED_REPLY, PHYSICAL_FAILURE, DUPLICATE_REQUEST |
| [035](035.md) | Merchant has received the return but the refund review has not started | 6 | CHANNEL_FAILURE, CONFLICTING_RECORDS, UNAUTHORISED_REPLY, OUT_OF_POLICY_ASK, CUSTOMER_CANCELS, DUPLICATE_REQUEST |
| [036](036.md) | Business sender needs collection of several labelled cartons | 6 | STALE_STATE, CHANNEL_FAILURE, PHYSICAL_FAILURE, UNAUTHORISED_REPLY, CONFLICTING_RECORDS, DUPLICATE_REQUEST |
| [037](037.md) | Customer needs an eligible heavy item collected from inside the home | 6 | STALE_STATE, OUT_OF_POLICY_ASK, CHANNEL_FAILURE, PHYSICAL_FAILURE, UNAUTHORISED_REPLY, CUSTOMER_CANCELS |
| [038](038.md) | Failed delivery has returned to sender and the customer still wants the order | 6 | SNAPSHOT_CONFLICT, STALE_STATE, CHANNEL_FAILURE, CONFLICTING_RECORDS, CUSTOMER_CANCELS, DUPLICATE_REQUEST |
| [039](039.md) | Merchant shipped a replacement but the original parcel then also arrived | 5 | CHANNEL_FAILURE, CONFLICTING_RECORDS, STALE_STATE, OUT_OF_POLICY_ASK, UNAUTHORISED_REPLY |
| [040](040.md) | Cancelled order is packed but has not left the merchant warehouse | 6 | STALE_STATE, CHANNEL_FAILURE, SNAPSHOT_CONFLICT, CONFLICTING_RECORDS, OUT_OF_POLICY_ASK, NO_REPLY |
| [041](041.md) | Pallet delivery lacks a receiving-dock appointment | 6 | UNAUTHORISED_REPLY, STALE_STATE, CHANNEL_FAILURE, NO_REPLY, CONFLICTING_RECORDS, OUT_OF_POLICY_ASK |
| [042](042.md) | Warehouse has no forklift for a booked pallet delivery | 6 | AMBIGUOUS_REPLY, UNAUTHORISED_REPLY, CHANNEL_FAILURE, STALE_STATE, OUT_OF_POLICY_ASK, CONFLICTING_RECORDS |
| [043](043.md) | Freight collection needs confirmed pallet dimensions and weight | 6 | AMBIGUOUS_REPLY, CONFLICTING_RECORDS, STALE_STATE, CHANNEL_FAILURE, NO_REPLY, OUT_OF_POLICY_ASK |
| [044](044.md) | One pallet is absent from a business consignment | 6 | CONFLICTING_RECORDS, UNAUTHORISED_REPLY, STALE_STATE, DUPLICATE_REQUEST, CUSTOMER_CANCELS, NO_REPLY |
| [045](045.md) | Import shipment is waiting for the shipper's commercial invoice | 5 | UNAUTHORISED_REPLY, AMBIGUOUS_REPLY, OUT_OF_POLICY_ASK, CONFLICTING_RECORDS, NEEDS_HUMAN |
| [046](046.md) | Import broker needs the consignee to appoint it before processing | 6 | SNAPSHOT_CONFLICT, UNAUTHORISED_REPLY, CHANNEL_FAILURE, CONFLICTING_RECORDS, OUT_OF_POLICY_ASK, NO_REPLY |
| [047](047.md) | Customer asks for an explanation of a carrier-issued import charge | 5 | AMBIGUOUS_REPLY, CONFLICTING_RECORDS, UNAUTHORISED_REPLY, CHANNEL_FAILURE, OUT_OF_POLICY_ASK |
| [048](048.md) | International shipment is cleared but awaiting last-mile handover | 5 | AMBIGUOUS_REPLY, CONFLICTING_RECORDS, UNAUTHORISED_REPLY, CUSTOMER_CANCELS, STALE_STATE |
| [049](049.md) | Duplicate delivery service charge appears on a business invoice | 5 | CONFLICTING_RECORDS, OUT_OF_POLICY_ASK, STALE_STATE, DUPLICATE_REQUEST, UNAUTHORISED_REPLY |
| [050](050.md) | Customer requests reimbursement of a guaranteed-delivery surcharge after confirmed delay | 5 | OUT_OF_POLICY_ASK, CONFLICTING_RECORDS, UNAUTHORISED_REPLY, DUPLICATE_REQUEST, CUSTOMER_CANCELS |

## Totals

| Failure mode | Branches |
|---|---|
| CONFLICTING_RECORDS | 43 |
| UNAUTHORISED_REPLY | 40 |
| STALE_STATE | 34 |
| CHANNEL_FAILURE | 34 |
| OUT_OF_POLICY_ASK | 31 |
| NO_REPLY | 18 |
| CUSTOMER_CANCELS | 17 |
| AMBIGUOUS_REPLY | 16 |
| DUPLICATE_REQUEST | 15 |
| SNAPSHOT_CONFLICT | 10 |
| PHYSICAL_FAILURE | 10 |
| NEEDS_HUMAN | 7 |

| Expected decision | Branches |
|---|---|
| SEPARATE_AUTHORITY | 45 |
| RECONCILE_CONFLICT | 43 |
| ASK_CUSTOMER | 35 |
| DECLINE_EXPLAIN | 35 |
| VERIFY_FIRST | 34 |
| WAIT_WITH_DEADLINE | 18 |
| RECORD_STOP | 17 |
| RESOLVE_DUPLICATE | 15 |
| GET_OPTIONS | 13 |
| REQUEST_ACTION | 9 |
| ESCALATE_OPERATOR | 8 |
| RECORD_REFUSAL | 3 |

| Sheet | Branches |
|---|---|
| A | 90 |
| B | 58 |
| C | 4 |
| D | 5 |
| E | 52 |
| F | 32 |
| R | 34 |

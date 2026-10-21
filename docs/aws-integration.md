# AWS integration (AWS Builder mini challenge)

| AWS service | Where in code | What it does in ChronoGrid |
| --- | --- | --- |
| **Strands Agents SDK** | [`agent/alexa_agent.py`](../agent/alexa_agent.py) | The Alexa+ brain. `Agent` + `BedrockModel` + `MCPClient(url=".../mcp")` loads ChronoGrid's MCP tools over Streamable HTTP. Uses `SlidingWindowConversationManager`, `S3SessionManager`, and a `BeforeToolCallEvent` hook for the on-screen tool trace. |
| **Amazon Bedrock: Amazon Nova 2 Lite** (`us.amazon.nova-2-lite-v1:0`) | `server/config.py` (`CHRONOGRID_MODEL_ID`) | Interprets voice requests, picks git-verb tools, and **compiles natural-language safety rules into typed ChronoLint rules** via the `propose_lint_rule` tool schema. Answers in about 3 s end to end. Any Bedrock Converse model with tool use can be swapped in via `CHRONOGRID_MODEL_ID` (e.g. Claude Haiku 4.5 once Anthropic access is enabled on the account). |
| **Amazon Polly** (generative, falling back to neural) | [`agent/voice.py`](../agent/voice.py), `/api/tts` | Alexa+'s voice on the ambient screen: replies and spoken hazard announcements. |
| **Amazon S3** | [`server/storage.py`](../server/storage.py), `S3SessionManager` | Private bucket (all public access blocked) for the face-blurred rewind clips, served to the screen and MCP App through **presigned URLs**, with a **7-day lifecycle expiry** under `clips/`. The same bucket holds Strands **session memory** under `sessions/`, so the assistant remembers context across restarts and devices. |

## Setup used
```powershell
$b = "chronogrid-clips-<account-id>"
aws s3api create-bucket --bucket $b --region us-east-1
aws s3api put-public-access-block --bucket $b --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
aws s3api put-bucket-lifecycle-configuration --bucket $b --lifecycle-configuration '{"Rules":[{"ID":"expire-clips-7d","Status":"Enabled","Filter":{"Prefix":"clips/"},"Expiration":{"Days":7}}]}'
```
Then set `CHRONOGRID_S3_BUCKET` in `.env`. Without it, clips are served locally and sessions are stored in `data/sessions/`.

## Minimal IAM policy
```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow", "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream", "bedrock:Converse", "bedrock:ConverseStream"], "Resource": "*" },
    { "Effect": "Allow", "Action": ["polly:SynthesizeSpeech"], "Resource": "*" },
    { "Effect": "Allow", "Action": ["s3:GetObject", "s3:PutObject", "s3:ListBucket", "s3:DeleteObject"],
      "Resource": ["arn:aws:s3:::chronogrid-clips-*", "arn:aws:s3:::chronogrid-clips-*/*"] }
  ]
}
```

## Design choice: deterministic boundary
Bedrock is used where language is ambiguous: interpreting requests and turning "a couple of minutes" into `for_seconds: 120`. Facts and safety decisions are deterministic: locations and times come from the ledger, and alerts come from `server/rules.py`. That keeps a safety feature auditable, which an LLM-judged alert would not be.

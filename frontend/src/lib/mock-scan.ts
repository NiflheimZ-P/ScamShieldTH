// Mock SSE stream for UI work while the backend agent is being built (NEXT_PUBLIC_SCAN_MOCK=1).
// Scenarios are the designer's sample messages from the Claude Design export — not evaluation data.

import type { Channel, ScanEvent, ScanRequest, Tone, ToolName, Verdict } from "./types";

type MockStep = [tool: ToolName, args: Record<string, string>, summary: string, tone: Tone];

interface Scenario {
  channel: Channel;
  title: { th: string; en: string };
  message: string;
  steps: MockStep[];
  verdict: Verdict;
}

export const SCENARIOS = {
  parcel: {
    channel: "sms",
    title: { th: "พัสดุตกค้าง", en: "Parcel held" },
    message:
      "TH-POST: พัสดุของคุณตกค้างที่ศูนย์คัดแยก เนื่องจากที่อยู่ไม่ครบ กรุณาชำระค่าธรรมเนียม 25 บาท ภายใน 24 ชม. ที่ https://thaipost-th.co/pay มิฉะนั้นพัสดุจะถูกตีกลับ สอบถาม 08x-xxx-1234",
    steps: [
      ["search_advisories", { query: "พัสดุตกค้าง ลิงก์ชำระค่าธรรมเนียม" }, "พบคำเตือน 3 ฉบับที่ตรงกัน", "warn"],
      ["check_indicator", { kind: "domain", value: "thaipost-th.co" }, "ชื่อคล้าย thailandpost.co.th · โดเมนอายุ 6 วัน", "warn"],
      ["inspect_url", { url: "https://thaipost-th.co/pay" }, "หน้าเว็บขอเลขบัตร วันหมดอายุ และ CVV", "warn"],
      ["check_indicator", { kind: "phone", value: "08x-xxx-1234" }, "ถูกแจ้งว่าเป็นมิจฉาชีพ 12 ครั้ง", "warn"],
    ],
    verdict: {
      scam_type: "fake_parcel",
      risk_level: "high",
      summary:
        "ข้อความนี้เลียนแบบไปรษณีย์เพื่อหลอกให้กดลิงก์และกรอกข้อมูลบัตร ลิงก์พาไปเว็บปลอมที่ชื่อคล้ายของจริง และเบอร์ติดต่อเคยถูกแจ้งหลายครั้ง",
      red_flags: [
        { text: "ขอให้จ่ายค่าธรรมเนียมผ่านลิงก์ใน SMS ไปรษณีย์ไม่เรียกเก็บเงินด้วยวิธีนี้", quote: "ชำระค่าธรรมเนียม 25 บาท" },
        { text: "เร่งให้รีบทำภายใน 24 ชั่วโมง เพื่อไม่ให้มีเวลาคิด", quote: "ภายใน 24 ชม." },
        { text: "ลิงก์ thaipost-th.co ตั้งชื่อเลียนแบบเว็บจริง thailandpost.co.th และเพิ่งจดทะเบียน 6 วัน", quote: "https://thaipost-th.co/pay" },
        { text: "เบอร์ 08x-xxx-1234 ถูกแจ้งว่าเป็นมิจฉาชีพ 12 ครั้ง", quote: "08x-xxx-1234" },
      ],
      recommended_actions: [
        { text: "อย่ากดลิงก์ และอย่ากรอกข้อมูลบัตรหรือรหัสใด ๆ" },
        { text: "ถ้าเผลอกรอกข้อมูลบัตรไปแล้ว ให้โทรอายัดบัตรกับธนาคารทันที", note: "ใช้เบอร์หลังบัตรหรือในแอปธนาคาร" },
        { text: "แจ้งสายด่วนตำรวจไซเบอร์", phone: "1441" },
        { text: "ลบข้อความ และบล็อกเบอร์ผู้ส่ง" },
      ],
      citations: [
        { title: "เตือนภัย SMS ปลอมอ้างพัสดุตกค้าง หลอกให้ชำระค่าธรรมเนียม", source: "ตำรวจไซเบอร์", url: "https://ccib.go.th" },
        { title: "รู้ทันลิงก์ปลอม ดูชื่อเว็บให้ดีก่อนกด", source: "ธปท.", url: "https://bot.or.th" },
        { title: "วิธีสังเกตเว็บไซต์ปลอมและช่องทางแจ้งเหตุ", source: "ETDA 1212", url: "https://1212etda.com" },
      ],
    },
  },
  job: {
    channel: "line",
    title: { th: "งานออนไลน์ทำที่บ้าน", en: "Work-from-home job" },
    message:
      "สวัสดีค่ะ บริษัทเรากำลังรับสมัครงานออนไลน์ทำที่บ้าน แค่กดไลก์และรีวิวสินค้า รายได้วันละ 500–3,000 บาท ไม่ต้องมีประสบการณ์ สนใจแอดไลน์ @jobhome88 ได้เลยค่ะ",
    steps: [
      ["search_advisories", { query: "งานออนไลน์ กดไลก์ รีวิวสินค้า รายได้ต่อวัน" }, "พบคำเตือน 2 ฉบับที่คล้ายกัน", "warn"],
      ["check_indicator", { kind: "line_id", value: "@jobhome88" }, "ไม่พบในรายการที่ถูกแจ้ง", "info"],
    ],
    verdict: {
      scam_type: "job_task",
      risk_level: "medium",
      summary:
        "รูปแบบคล้ายมิจฉาชีพหลอกทำงานออนไลน์ แต่ยังไม่พบหลักฐานว่า LINE ID นี้ถูกแจ้ง จึงยังสรุปไม่ได้แน่ชัด ให้ระวังเป็นพิเศษถ้าถูกขอให้โอนเงิน",
      red_flags: [
        { text: "งานง่ายแบบกดไลก์หรือรีวิว เป็นรูปแบบที่พบบ่อยในมิจฉาชีพหลอกทำงาน", quote: "งานออนไลน์ทำที่บ้าน แค่กดไลก์และรีวิวสินค้า" },
        { text: "รายได้สูงเกินจริงสำหรับงานที่ไม่ต้องใช้ทักษะ", quote: "รายได้วันละ 500–3,000 บาท" },
        { text: "ชวนไปคุยต่อในบัญชี LINE ส่วนตัว (ยังไม่พบในรายการที่ถูกแจ้ง)", quote: "@jobhome88" },
      ],
      recommended_actions: [
        { text: "อย่าโอนเงินค่าสมัคร ค่ามัดจำ หรือ “เติมเงินเพื่อรับงาน” ไม่ว่ากรณีใด" },
        { text: "ค้นชื่อบริษัทและตรวจว่ามีตัวตนจริงก่อนติดต่อ" },
        { text: "ถ้าถูกขอให้โอนเงิน ให้หยุดคุยและโทรปรึกษา", phone: "1441" },
      ],
      citations: [
        { title: "ระวังมิจฉาชีพหลอกทำงานออนไลน์ กดไลก์รับเงิน", source: "ตำรวจไซเบอร์", url: "https://ccib.go.th" },
        { title: "ภัยหลอกให้ลงทุนหรือทำงานผ่านโซเชียลมีเดีย", source: "ธปท.", url: "https://bot.or.th" },
      ],
    },
  },
  otp: {
    channel: "sms",
    title: { th: "รหัส OTP จากธนาคาร", en: "Bank OTP" },
    message:
      "รหัส OTP ของคุณคือ 48••13 (Ref: KX7Q) สำหรับเข้าสู่ระบบแอปธนาคาร ห้ามบอกรหัสนี้กับผู้อื่น ธนาคารไม่มีนโยบายขอรหัส OTP ทางโทรศัพท์",
    steps: [
      ["search_advisories", { query: "SMS รหัส OTP ธนาคาร เข้าสู่ระบบ" }, "พบแนวทางของ ธปท. 1 ฉบับ ตรงกับรูปแบบข้อความจริง", "ok"],
    ],
    verdict: {
      scam_type: "legit",
      risk_level: "low",
      summary:
        "รูปแบบตรงกับ SMS แจ้งรหัส OTP ของธนาคาร ไม่มีลิงก์ ไม่ขอให้โทรกลับ และเตือนไม่ให้บอกรหัสกับใคร แต่ให้ใช้รหัสเฉพาะเมื่อคุณทำรายการเองเท่านั้น",
      red_flags: [{ text: "ถ้าคุณไม่ได้กำลังเข้าสู่ระบบเองตอนนี้ แปลว่าอาจมีคนพยายามเข้าบัญชีของคุณ", quote: "48••13" }],
      recommended_actions: [
        { text: "ใช้รหัสนี้เฉพาะเมื่อคุณกำลังทำรายการเองเท่านั้น" },
        { text: "ห้ามบอกรหัสกับใคร แม้จะอ้างว่าเป็นเจ้าหน้าที่ธนาคาร" },
        { text: "ถ้าไม่ได้ทำรายการเอง ให้โทรหาธนาคารจากเบอร์หลังบัตร" },
      ],
      citations: [{ title: "ธนาคารไม่มีนโยบายขอรหัส OTP ทางโทรศัพท์หรือข้อความ", source: "ธปท.", url: "https://bot.or.th" }],
    },
  },
  promo: {
    channel: "sms",
    title: { th: "โปรโมชันร้านค้า (ไทย-อังกฤษ)", en: "Shop promo (mixed TH-EN)" },
    message: "MyShop: Flash Sale 11.11 ลดสูงสุด 50% เฉพาะในแอป MyShop เท่านั้น Free shipping all orders. ยกเลิกรับข่าวสารกด *137*1",
    steps: [["search_advisories", { query: "Flash Sale ส่วนลด ยกเลิกรับข่าวสาร" }, "ไม่พบคำเตือนที่ตรงกัน", "ok"]],
    verdict: {
      scam_type: "other",
      risk_level: "low",
      summary: "ข้อความโฆษณาทั่วไป ไม่มีลิงก์ ไม่ขอข้อมูลส่วนตัว และไม่เร่งให้โอนเงิน",
      red_flags: [],
      recommended_actions: [
        { text: "ถ้าสนใจโปรโมชัน ให้เปิดดูในแอปที่คุณติดตั้งเองแทนการกดลิงก์" },
        { text: "ถ้ามีข้อความต่อมาขอให้กรอกข้อมูลหรือโอนเงิน ให้ตรวจใหม่อีกครั้ง" },
      ],
      citations: [],
    },
  },
  short: {
    channel: "line",
    title: { th: "ข้อความสั้น", en: "Short message" },
    message: "โอนแล้วนะ เช็กด้วย",
    steps: [["search_advisories", { query: "โอนแล้ว เช็กด้วย" }, "ไม่พบคำเตือนที่ตรงกัน", "info"]],
    verdict: {
      scam_type: "other",
      risk_level: "unknown",
      summary: "ข้อความสั้นเกินไป ไม่มีลิงก์ เบอร์ หรือรายละเอียดพอให้ตัดสินได้",
      red_flags: [],
      recommended_actions: [
        { text: "ถ้าไม่ได้รอรับเงินจากใคร อย่าเชื่อจนกว่าจะเห็นยอดเงินในแอปธนาคารของคุณเอง" },
        { text: "อย่าโอนเงินคืนให้ใครตามคำขอในแชท" },
        { text: "คัดลอกข้อความทั้งหมด รวมชื่อผู้ส่ง แล้วตรวจอีกครั้ง" },
      ],
      citations: [],
    },
  },
} satisfies Record<string, Scenario>;

type ScenarioKey = keyof typeof SCENARIOS;

export const EXAMPLE_KEYS: ScenarioKey[] = ["parcel", "job", "otp", "promo"];

function pick(message: string): ScenarioKey {
  const text = message.trim();
  const hit = (Object.keys(SCENARIOS) as ScenarioKey[]).find((k) => SCENARIOS[k].message === text);
  if (hit) return hit;
  if (text.length < 25) return "short";
  return /https?:\/\/|www\./i.test(text) ? "parcel" : "job";
}

function sleep(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const t = setTimeout(resolve, ms);
    signal.addEventListener("abort", () => {
      clearTimeout(t);
      reject(new DOMException("Aborted", "AbortError"));
    });
  });
}

export async function* mockScan(req: ScanRequest, signal: AbortSignal): AsyncGenerator<ScanEvent> {
  const sc: Scenario = SCENARIOS[pick(req.message)];
  await sleep(900, signal);
  for (const [i, [tool, args, summary, tone]] of sc.steps.entries()) {
    const id = `mock-${i}`;
    yield { type: "step", id, tool, args };
    await sleep(1500 + (i % 2) * 700, signal);
    yield { type: "observation", id, tool, summary, tone };
    await sleep(450, signal);
  }
  yield { type: "summarizing" };
  await sleep(1600, signal);
  yield { type: "verdict", verdict: sc.verdict }; // quotes absent from the message are simply not highlighted
}

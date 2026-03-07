import { NextRequest, NextResponse } from 'next/server'
import { Resend } from 'resend'

const resend = new Resend(process.env.RESEND_API_KEY)
const OWNER_EMAIL = 'hello@sheetmind.xyz'
const FROM_EMAIL = process.env.RESEND_FROM_EMAIL ?? 'SheetMind <onboarding@resend.dev>'

export async function POST(req: NextRequest) {
  try {
    const { name, email, subject, message } = await req.json()

    if (!name || !email || !message) {
      return NextResponse.json({ error: 'Missing required fields.' }, { status: 400 })
    }

    // 1. Notify the owner
    await resend.emails.send({
      from: FROM_EMAIL,
      to: OWNER_EMAIL,
      replyTo: email,
      subject: `[SheetMind Contact] ${subject ?? 'General inquiry'} — from ${name}`,
      html: `
        <div style="font-family:system-ui,sans-serif;max-width:600px;padding:32px;background:#f8fafc;border-radius:12px;">
          <div style="background:#10b981;color:white;padding:16px 24px;border-radius:8px;margin-bottom:24px;">
            <strong style="font-size:18px;">New Contact Form Submission</strong>
          </div>
          <table style="width:100%;border-collapse:collapse;">
            <tr><td style="padding:8px 0;color:#64748b;font-size:13px;width:100px;">Name</td><td style="padding:8px 0;font-weight:600;color:#0f172a;">${name}</td></tr>
            <tr><td style="padding:8px 0;color:#64748b;font-size:13px;">Email</td><td style="padding:8px 0;"><a href="mailto:${email}" style="color:#10b981;">${email}</a></td></tr>
            <tr><td style="padding:8px 0;color:#64748b;font-size:13px;">Subject</td><td style="padding:8px 0;color:#0f172a;">${subject ?? 'General inquiry'}</td></tr>
          </table>
          <div style="margin-top:16px;padding:16px;background:white;border-radius:8px;border:1px solid #e2e8f0;">
            <p style="margin:0;color:#334155;font-size:14px;line-height:1.6;white-space:pre-wrap;">${message}</p>
          </div>
          <p style="margin-top:16px;font-size:12px;color:#94a3b8;">Reply directly to this email to respond to ${name}.</p>
        </div>
      `,
    })

    // 2. Send confirmation to the user
    await resend.emails.send({
      from: FROM_EMAIL,
      to: email,
      subject: "We got your message — SheetMind",
      html: `
        <div style="font-family:system-ui,sans-serif;max-width:600px;padding:32px;">
          <div style="display:flex;align-items:center;gap:12px;margin-bottom:24px;">
            <div style="width:40px;height:40px;background:linear-gradient(135deg,#10b981,#047857);border-radius:10px;display:flex;align-items:center;justify-content:center;">
              <span style="color:white;font-size:20px;">✦</span>
            </div>
            <span style="font-size:22px;font-weight:800;"><span style="color:#0f172a;">Sheet</span><span style="color:#10b981;">Mind</span></span>
          </div>
          <h2 style="font-size:20px;font-weight:700;color:#0f172a;margin:0 0 12px;">Thanks for reaching out, ${name}!</h2>
          <p style="color:#475569;font-size:15px;line-height:1.7;margin:0 0 24px;">
            We've received your message and will get back to you as soon as possible — usually within 24 hours.
          </p>
          <div style="background:#f1f5f9;border-radius:8px;padding:16px;margin-bottom:24px;">
            <p style="margin:0 0 8px;font-size:13px;color:#64748b;font-weight:600;">YOUR MESSAGE</p>
            <p style="margin:0;font-size:14px;color:#334155;line-height:1.6;white-space:pre-wrap;">${message}</p>
          </div>
          <p style="color:#64748b;font-size:13px;margin:0;">
            If your issue is urgent, you can also reach us at
            <a href="mailto:${OWNER_EMAIL}" style="color:#10b981;">${OWNER_EMAIL}</a>.
          </p>
          <hr style="border:none;border-top:1px solid #e2e8f0;margin:24px 0;" />
          <p style="color:#94a3b8;font-size:12px;margin:0;">SheetMind · AI for Google Sheets · <a href="https://sheetmind.xyz" style="color:#94a3b8;">sheetmind.xyz</a></p>
        </div>
      `,
    })

    return NextResponse.json({ success: true })
  } catch (err) {
    console.error('[contact]', err)
    return NextResponse.json({ error: 'Failed to send message. Please try again.' }, { status: 500 })
  }
}

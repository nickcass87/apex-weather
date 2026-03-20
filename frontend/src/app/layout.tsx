import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Apex Weather — Motorsport Weather Intelligence",
  description:
    "Hyper-local weather predictions for 60+ racing circuits worldwide. Track temperature, rain probability, wind analysis, grip conditions, and surface drying forecasts.",
  openGraph: {
    title: "Apex Weather — Motorsport Weather Intelligence",
    description:
      "Hyper-local weather predictions for 60+ racing circuits worldwide.",
    type: "website",
    siteName: "Apex Weather",
  },
  twitter: {
    card: "summary_large_image",
    title: "Apex Weather — Motorsport Weather Intelligence",
    description:
      "Hyper-local weather predictions for 60+ racing circuits worldwide.",
  },
  robots: { index: true, follow: true },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link
          rel="stylesheet"
          href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
          crossOrigin=""
        />
        <link
          rel="preconnect"
          href="https://fonts.googleapis.com"
        />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin=""
        />
      </head>
      <body className="min-h-screen">{children}</body>
    </html>
  );
}

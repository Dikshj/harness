
export const metadata = {
  title: 'Autonomous Harness',
  description: 'Agentic AI software engineering harness',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-gray-950 text-gray-100 min-h-screen">{children}</body>
    </html>
  );
}

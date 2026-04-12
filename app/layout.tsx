import { Outfit } from "next/font/google"

import "./globals.css"
import { ThemeProvider } from "@/components/theme-provider"
import { cn } from "@/lib/utils"
import { TooltipProvider } from "@/components/ui/tooltip"

const font = Outfit({
  subsets: ["latin"],
  variable: "--font-outfit",
})

export const metadata = {
  title: "ASV - Apex Stock View",
  description: "A quant tool for visualizing stock data and backtesting trading strategies.",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={cn("antialiased", font.variable, "font-outfit")}
    >
      <body>
        <ThemeProvider>
          <TooltipProvider>
              <main>
                {children}
              </main>
          </TooltipProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}
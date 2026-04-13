"use client"

import * as React from "react"

type Theme = "light" | "dark" | "system"
type ResolvedTheme = Exclude<Theme, "system">

type ThemeContextValue = {
  theme: Theme
  resolvedTheme: ResolvedTheme
  setTheme: (theme: Theme) => void
}

type ThemeProviderProps = React.PropsWithChildren<{
  attribute?: "class" | string
  defaultTheme?: Theme
  disableTransitionOnChange?: boolean
  enableSystem?: boolean
  storageKey?: string
}>

const STORAGE_KEY = "theme"
const ThemeContext = React.createContext<ThemeContextValue | null>(null)

function getSystemTheme(): ResolvedTheme {
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light"
}

function getStoredTheme(storageKey: string) {
  try {
    const value = window.localStorage.getItem(storageKey)
    if (value === "light" || value === "dark" || value === "system") {
      return value
    }
  } catch {
    return null
  }

  return null
}

function disableTransitionsTemporarily() {
  const style = document.createElement("style")
  style.appendChild(
    document.createTextNode(
      "*,*::before,*::after{-webkit-transition:none!important;transition:none!important}"
    )
  )
  document.head.appendChild(style)

  return () => {
    window.getComputedStyle(document.body)
    requestAnimationFrame(() => {
      style.remove()
    })
  }
}

function applyTheme({
  attribute,
  disableTransitionOnChange,
  enableSystem,
  theme,
}: {
  attribute: string
  disableTransitionOnChange: boolean
  enableSystem: boolean
  theme: Theme
}) {
  const resolvedTheme =
    theme === "system" && enableSystem ? getSystemTheme() : theme === "system" ? "light" : theme
  const root = document.documentElement
  const cleanup = disableTransitionOnChange ? disableTransitionsTemporarily() : null

  if (attribute === "class") {
    root.classList.remove("light", "dark")
    root.classList.add(resolvedTheme)
  } else {
    root.setAttribute(attribute, resolvedTheme)
  }

  root.style.colorScheme = resolvedTheme
  cleanup?.()

  return resolvedTheme
}

function ThemeProvider({
  children,
  attribute = "class",
  defaultTheme = "dark",
  disableTransitionOnChange = true,
  enableSystem = true,
  storageKey = STORAGE_KEY,
}: ThemeProviderProps) {
  const [theme, setThemeState] = React.useState<Theme>(defaultTheme)
  const [resolvedTheme, setResolvedTheme] = React.useState<ResolvedTheme>("light")

  React.useLayoutEffect(() => {
    const storedTheme = getStoredTheme(storageKey)
    const nextTheme = storedTheme ?? defaultTheme

    setThemeState(nextTheme)
    setResolvedTheme(
      applyTheme({
        attribute,
        disableTransitionOnChange,
        enableSystem,
        theme: nextTheme,
      })
    )
  }, [attribute, defaultTheme, disableTransitionOnChange, enableSystem, storageKey])

  React.useEffect(() => {
    if (!enableSystem) {
      return
    }

    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)")
    const handleChange = () => {
      if (theme !== "system") {
        return
      }

      setResolvedTheme(
        applyTheme({
          attribute,
          disableTransitionOnChange,
          enableSystem,
          theme,
        })
      )
    }

    mediaQuery.addEventListener("change", handleChange)

    return () => {
      mediaQuery.removeEventListener("change", handleChange)
    }
  }, [attribute, disableTransitionOnChange, enableSystem, theme])

  React.useEffect(() => {
    const handleStorage = (event: StorageEvent) => {
      if (event.key !== storageKey) {
        return
      }

      const nextTheme =
        event.newValue === "light" ||
        event.newValue === "dark" ||
        event.newValue === "system"
          ? event.newValue
          : defaultTheme

      setThemeState(nextTheme)
      setResolvedTheme(
        applyTheme({
          attribute,
          disableTransitionOnChange,
          enableSystem,
          theme: nextTheme,
        })
      )
    }

    window.addEventListener("storage", handleStorage)

    return () => {
      window.removeEventListener("storage", handleStorage)
    }
  }, [attribute, defaultTheme, disableTransitionOnChange, enableSystem, storageKey])

  const setTheme = React.useCallback(
    (nextTheme: Theme) => {
      setThemeState(nextTheme)

      try {
        window.localStorage.setItem(storageKey, nextTheme)
      } catch {
        // Ignore storage failures and still update the current document theme.
      }

      setResolvedTheme(
        applyTheme({
          attribute,
          disableTransitionOnChange,
          enableSystem,
          theme: nextTheme,
        })
      )
    },
    [attribute, disableTransitionOnChange, enableSystem, storageKey]
  )

  const value = React.useMemo<ThemeContextValue>(
    () => ({ theme, resolvedTheme, setTheme }),
    [theme, resolvedTheme, setTheme]
  )

  return (
    <ThemeContext.Provider value={value}>
      <ThemeHotkey />
      {children}
    </ThemeContext.Provider>
  )
}

function isTypingTarget(target: EventTarget | null) {
  if (!(target instanceof HTMLElement)) {
    return false
  }

  return (
    target.isContentEditable ||
    target.tagName === "INPUT" ||
    target.tagName === "TEXTAREA" ||
    target.tagName === "SELECT"
  )
}

function ThemeHotkey() {
  const { resolvedTheme, setTheme } = useTheme()

  React.useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.defaultPrevented || event.repeat) {
        return
      }

      if (event.metaKey || event.ctrlKey || event.altKey) {
        return
      }

      if (event.key.toLowerCase() !== "d") {
        return
      }

      if (isTypingTarget(event.target)) {
        return
      }

      setTheme(resolvedTheme === "dark" ? "light" : "dark")
    }

    window.addEventListener("keydown", onKeyDown)

    return () => {
      window.removeEventListener("keydown", onKeyDown)
    }
  }, [resolvedTheme, setTheme])

  return null
}

function useTheme() {
  const context = React.useContext(ThemeContext)

  if (!context) {
    throw new Error("useTheme must be used within a ThemeProvider.")
  }

  return context
}

export { ThemeProvider, useTheme }

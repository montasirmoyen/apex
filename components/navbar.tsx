"use client";

import { Menu, Zap, LogOut, User } from "lucide-react";

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Button } from "@/components/ui/button";
import {
  NavigationMenu,
  NavigationMenuContent,
  NavigationMenuItem,
  NavigationMenuLink,
  NavigationMenuList,
  NavigationMenuTrigger,
} from "@/components/ui/navigation-menu";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import { cn } from "@/lib/utils";
import { useRouter } from "next/navigation";

interface MenuItem {
  title: string;
  url: string;
  description?: string;
  icon?: React.ReactNode;
  items?: MenuItem[];
  authRequired?: boolean;
}

interface NavbarProps {
  className?: string;
  logo?: {
    url: string;
    image: string;
    alt: string;
    title: string;
    className?: string;
  };
  menu?: MenuItem[];
  auth?: {
    login: {
      title: string;
      url: string;
    };
    signup: {
      title: string;
      url: string;
    };
  };
}

const Navbar = ({
  logo = {
    url: "/",
    image: "/apex-white.png",
    alt: "Apex Logo",
    title: "Apex",
  },
  menu = [
    { title: "Home", url: "/" },
    {
      title: "Dashboard",
      url: "/dashboard",
      authRequired: true,
    },
    {
      title: "Documents",
      url: "/documents",
      authRequired: true,
    },
  ],
  auth = {
    login: { title: "Login", url: "/login" },
    signup: { title: "Sign up", url: "/register" },
  },
  className,
}: NavbarProps) => {
  const user = null; // Replace with actual authentication hook or context
  const loading = false; // Replace with actual loading state
  const signOut = async () => {}; // Replace with actual sign out function
  const router = useRouter();

  const filteredMenu = menu.filter(
    (item) => !item.authRequired || user
  );

  const handleSignOut = async () => {
    await signOut();
    // Use Next.js router to avoid a full page reload (maintains SPA state)
    router.push("/");
  };

  return (
    <section className={cn("py-4", className)}>
      <div className="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Desktop Menu */}
        <nav className="hidden w-full items-center justify-between gap-8 lg:flex">
          <div className="flex min-w-0 items-center gap-8">
            {/* Logo */}
            <a href={logo.url} className="flex items-center gap-2">
              <img src={logo.image} alt={logo.alt} className="h-8 w-8" />
              <span className="text-lg font-semibold tracking-tighter">
                {logo.title}
              </span>
            </a>
            <div className="flex items-center">
              <NavigationMenu>
                <NavigationMenuList>
                  {filteredMenu.map((item) => renderMenuItem(item))}
                </NavigationMenuList>
              </NavigationMenu>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2 pl-6">
            {loading ? null : user ? (
              <>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <User className="size-4" />
                </div>
                <Button variant="outline" size="sm" onClick={handleSignOut}>
                  <LogOut className="size-4" />
                  Logout
                </Button>
              </>
            ) : (
              <>
                <Button asChild variant="outline" size="sm">
                  <a href={auth.login.url}>{auth.login.title}</a>
                </Button>
                <Button asChild size="sm">
                  <a href={auth.signup.url}>{auth.signup.title}</a>
                </Button>
              </>
            )}
            <ThemeToggle />
          </div>
        </nav>

        {/* Mobile Menu */}
        <div className="block lg:hidden">
          <div className="flex items-center justify-between">
            {/* Logo */}
            <a href={logo.url} className="flex items-center gap-2">
              <img src={logo.image} alt={logo.alt} className="h-8 w-8" />
              <span className="text-lg font-semibold tracking-tighter">
                {logo.title}
              </span>
            </a>
            
            <Sheet>
              <SheetTrigger asChild>
                <Button variant="outline" size="icon">
                  <Menu className="size-4" />
                </Button>
              </SheetTrigger>
              <SheetContent className="overflow-y-auto">
                <SheetHeader>
                  <SheetTitle>
                    <a href={logo.url} className="flex items-center gap-2">
                      <img src={logo.image} alt={logo.alt} className="h-8 w-8" />
                    </a>
                  </SheetTitle>
                </SheetHeader>
                <div className="flex flex-col gap-6 p-4">
                  <Accordion
                    type="single"
                    collapsible
                    className="flex w-full flex-col gap-4"
                  >
                    {filteredMenu.map((item) => renderMobileMenuItem(item))}
                  </Accordion>

                  <div className="flex flex-col gap-3">
                    {loading ? null : user ? (
                      <>
                        <div className="flex items-center gap-2 text-sm">
                          <User className="size-4" />
                        </div>
                        <Button variant="outline" onClick={handleSignOut}>
                          <LogOut className="size-4" />
                          Logout
                        </Button>
                      </>
                    ) : (
                      <>
                        <Button asChild variant="outline">
                          <a href={auth.login.url}>{auth.login.title}</a>
                        </Button>
                        <Button asChild>
                          <a href={auth.signup.url}>{auth.signup.title}</a>
                        </Button>
                      </>
                    )}
                    <ThemeToggle />
                  </div>
                </div>
              </SheetContent>
            </Sheet>
          </div>
        </div>
      </div>
    </section>
  );
};

const renderMenuItem = (item: MenuItem) => {
  if (item.items) {
    return (
      <NavigationMenuItem key={item.title}>
        <NavigationMenuTrigger>{item.title}</NavigationMenuTrigger>
        <NavigationMenuContent className="bg-popover text-popover-foreground">
          {item.items.map((subItem) => (
            <NavigationMenuLink asChild key={subItem.title} className="w-80">
              <SubMenuLink item={subItem} />
            </NavigationMenuLink>
          ))}
        </NavigationMenuContent>
      </NavigationMenuItem>
    );
  }

  return (
    <NavigationMenuItem key={item.title}>
      <NavigationMenuLink
        href={item.url}
        className="group inline-flex h-10 w-max items-center justify-center rounded-md bg-background px-4 py-2 text-sm font-medium transition-colors hover:bg-muted hover:text-accent-foreground"
      >
        {item.title}
      </NavigationMenuLink>
    </NavigationMenuItem>
  );
};

const renderMobileMenuItem = (item: MenuItem) => {
  if (item.items) {
    return (
      <AccordionItem key={item.title} value={item.title} className="border-b-0">
        <AccordionTrigger className="text-md py-0 font-semibold hover:no-underline">
          {item.title}
        </AccordionTrigger>
        <AccordionContent className="mt-2">
          {item.items.map((subItem) => (
            <SubMenuLink key={subItem.title} item={subItem} />
          ))}
        </AccordionContent>
      </AccordionItem>
    );
  }

  return (
    <a key={item.title} href={item.url} className="text-md font-semibold">
      {item.title}
    </a>
  );
};

const SubMenuLink = ({ item }: { item: MenuItem }) => {
  return (
    <a
      className="flex min-w-80 flex-row gap-4 rounded-md p-3 leading-none no-underline transition-colors outline-none select-none hover:bg-muted hover:text-accent-foreground"
      href={item.url}
    >
      <div className="text-foreground">{item.icon}</div>
      <div>
        <div className="text-sm font-semibold">{item.title}</div>
        {item.description && (
          <p className="text-sm leading-snug text-muted-foreground">
            {item.description}
          </p>
        )}
      </div>
    </a>
  );
};

export { Navbar };

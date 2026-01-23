"use client"

import Image from "next/image"
import { Lobster_Two } from "next/font/google"

const lobster = Lobster_Two({ subsets: ["latin"], weight: ["400", "700"], variable: "--font-lobster" })
import { Sparkles, UtensilsCrossed, Salad, Clock } from "lucide-react"

interface WelcomeScreenProps {
  onSuggestionClick: (suggestion: string) => void
}

const suggestions = [
  {
    icon: UtensilsCrossed,
    text: "I want to make pasta with chicken",
    label: "Quick dinner",
  },
  {
    icon: Salad,
    text: "Healthy vegetarian recipes under 500 calories",
    label: "Healthy eating",
  },
  {
    icon: Clock,
    text: "30-minute meals for busy weeknights",
    label: "Quick meals",
  },
  {
    icon: Sparkles,
    text: "Surprise me with something delicious",
    label: "Feeling adventurous",
  },
]

export function WelcomeScreen({ onSuggestionClick }: WelcomeScreenProps) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center px-4 pt-24 pb-12">
      <div className="-mb-2 flex justify-center select-none">
        <Image
          src="/feast-logo-full.png"
          alt="Feast"
          width={280}
          height={280}
          className="relative scale-[1.5] w-[420px] h-[420px] max-w-xs sm:max-w-md select-none pointer-events-none"
          draggable={false}
          onContextMenu={(e) => e.preventDefault()}
        />
      </div>

      <h2
        className={
          `text-3xl font-heading font-semibold text-foreground mt-0 mb-1 text-center tracking-tight ${lobster.variable} font-lobster`
        }
      >
        What are you craving?
      </h2>
      <p className="text-muted-foreground text-center max-w-md mb-8 -mt-1">
        Your AI-powered culinary companion. Ask about recipes, ingredients, or cooking techniques.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-xl">
        {suggestions.map((suggestion) => (
          <button
            key={suggestion.text}
            onClick={() => onSuggestionClick(suggestion.text)}
            className="group relative overflow-hidden rounded-xl border border-border bg-card/50 backdrop-blur-sm p-4 text-left transition-all duration-300 hover:border-primary/50 hover:bg-card/80"
          >
            <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
            <div className="relative">
              <div className="flex items-center gap-2 mb-2">
                <suggestion.icon className="w-4 h-4 text-primary" />
                <span className="text-xs font-medium text-primary uppercase tracking-wide">{suggestion.label}</span>
              </div>
              <span className="text-sm text-foreground/80 group-hover:text-foreground transition-colors">
                {suggestion.text}
              </span>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}

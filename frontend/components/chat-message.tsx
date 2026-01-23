"use client"

import { User } from "lucide-react"
import Image from "next/image"
import { RecipePreviewCard } from "@/components/recipe-preview-card"
import { FullRecipeCard } from "@/components/full-recipe-card"
import type { Message, RecipePreview } from "@/lib/types"

interface ChatMessageProps {
  message: Message
  onRecipeSelect: (preview: RecipePreview) => void
}

export function ChatMessage({ message, onRecipeSelect }: ChatMessageProps) {
  const isUser = message.role === "user"

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      <div
        className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
          isUser ? "bg-secondary" : "bg-primary/20"
        }`}
      >
        {isUser ? (
          <User className="w-4 h-4 text-foreground/80" />
        ) : (
          <Image src="/feast-logo.png" alt="Feast" width={18} height={18} className="opacity-80" />
        )}
      </div>

      <div className={`flex flex-col gap-4 max-w-[85%] ${isUser ? "items-end" : "items-start"}`}>
        <div
          className={`rounded-2xl px-5 py-4 shadow-sm transition-all duration-200 ${
            isUser 
              ? "bg-primary text-primary-foreground" 
              : "bg-[#1a1d24] border border-white/10 text-foreground shadow-lg shadow-black/20"
          }`}
        >
          <p className="text-sm whitespace-pre-wrap leading-relaxed">{message.content}</p>
        </div>

        {message.recipePreviews && message.recipePreviews.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 w-full mt-1">
            {message.recipePreviews.map((preview) => (
              <RecipePreviewCard key={preview.id} preview={preview} onClick={() => onRecipeSelect(preview)} />
            ))}
          </div>
        )}

        {message.fullRecipe && <FullRecipeCard recipe={message.fullRecipe} />}
      </div>
    </div>
  )
}

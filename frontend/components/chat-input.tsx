"use client"

import type React from "react"
import { useState, useRef, useEffect } from "react"
import { ArrowUp } from "lucide-react"
import { Button } from "@/components/ui/button"

interface ChatInputProps {
  onSend: (message: string) => void
  isLoading: boolean
}

export function ChatInput({ onSend, isLoading }: ChatInputProps) {
  const [input, setInput] = useState("")
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto"
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 150)}px`
    }
  }, [input])

  const handleSubmit = () => {
    if (input.trim() && !isLoading) {
      onSend(input.trim())
      setInput("")
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div className="relative">
      <div className="relative flex items-end gap-3 bg-[#12151a] border border-white/20 rounded-2xl p-3 transition-all duration-200 focus-within:border-primary/60 focus-within:shadow-[0_0_0_3px_rgba(255,138,61,0.15)] shadow-lg shadow-black/20">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="What would you like to cook today?"
          className="flex-1 resize-none bg-transparent border-0 focus:outline-none text-foreground placeholder:text-muted-foreground/70 min-h-[24px] max-h-[150px] text-sm pl-2"
          rows={1}
          disabled={isLoading}
        />
        <Button
          onClick={handleSubmit}
          disabled={!input.trim() || isLoading}
          size="icon"
          className="rounded-xl shrink-0 h-9 w-9 bg-primary hover:bg-primary/90 text-primary-foreground transition-all duration-200 hover:scale-105 disabled:opacity-40 disabled:hover:scale-100"
        >
          <ArrowUp className="w-4 h-4" />
          <span className="sr-only">Send message</span>
        </Button>
      </div>
    </div>
  )
}

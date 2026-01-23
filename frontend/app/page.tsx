"use client"

import { useState, useRef, useEffect } from "react"
import { ChatInput } from "@/components/chat-input"
import { ChatMessage } from "@/components/chat-message"
import { WelcomeScreen } from "@/components/welcome-screen"
import { Header } from "@/components/header"
import type { Message, RecipePreview, ConversationContext } from "@/lib/types"
import { sendChatMessage, expandRecipe, toPreview } from "@/lib/api"

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [context, setContext] = useState<ConversationContext>({})
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleHomeClick = () => {
    setMessages([])
    setContext({})
  }

  const handleSendMessage = async (content: string) => {
    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content,
    }

    setMessages((prev) => [...prev, userMessage])
    setIsLoading(true)

    try {
      // Build conversation history from messages
      const conversationHistory = messages.map((msg) => ({
        role: msg.role,
        content: msg.content,
      }))

      // Call backend API
      const response = await sendChatMessage(content, conversationHistory, context)

      // Update context with new information from backend
      setContext(response.context)

      // Convert recipes to previews if we have any
      const recipePreviews = response.recipes.length > 0 
        ? response.recipes.map(toPreview) 
        : undefined

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: response.message,
        recipePreviews,
      }

      setMessages((prev) => [...prev, assistantMessage])
    } catch (error) {
      console.error("Chat error:", error)
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "Sorry, I encountered an error. Please make sure the backend is running and try again.",
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleRecipeSelect = async (preview: RecipePreview) => {
    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: `Show me the full recipe for ${preview.title}`,
    }

    setMessages((prev) => [...prev, userMessage])
    setIsLoading(true)

    try {
      // Expand the recipe to get full details
      const fullRecipe = await expandRecipe(preview.id)

      // Generate a more conversational response
      const cookingTimeNote = fullRecipe.cooking_time 
        ? `It takes about ${fullRecipe.cooking_time} minutes` 
        : "It's pretty straightforward"
      
      const responseVariants = [
        `Great choice! ${fullRecipe.title} is a real winner. ${cookingTimeNote} - here's everything you need to make it.`,
        `Oh, you're going to love this one! ${cookingTimeNote}, and the result is totally worth it. Here's the full breakdown.`,
        `Perfect pick! ${fullRecipe.title} is one of those recipes that always delivers. ${cookingTimeNote} from start to finish.`,
        `Nice! This ${fullRecipe.cuisine || ''} dish is a crowd-pleaser. ${cookingTimeNote} - let me walk you through it.`,
      ]
      const randomResponse = responseVariants[Math.floor(Math.random() * responseVariants.length)]

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: randomResponse,
        fullRecipe,
      }

      setMessages((prev) => [...prev, assistantMessage])
    } catch (error) {
      console.error("Recipe expansion error:", error)
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "Sorry, I couldn't load that recipe. Please try again.",
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const hasMessages = messages.length > 0

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      {hasMessages && <Header onHomeClick={handleHomeClick} />}

      <main className="flex-1 overflow-y-auto overflow-x-hidden pb-32">
        <div className="max-w-3xl mx-auto w-full min-h-full flex flex-col">
          {!hasMessages ? (
            <div className="flex-1 flex flex-col pb-32">
              <WelcomeScreen onSuggestionClick={handleSendMessage} />
            </div>
          ) : (
            <div className="flex-1 px-4 py-6 pt-28 space-y-6">
              {messages.map((message) => (
                <ChatMessage key={message.id} message={message} onRecipeSelect={handleRecipeSelect} />
              ))}
              {isLoading && (
                <div className="flex items-start gap-3 px-2 animate-in fade-in duration-300">
                  <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
                    <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                  </div>
                  <div className="flex gap-1.5 pt-3">
                    <span
                      className="w-2 h-2 bg-primary/70 rounded-full animate-bounce"
                      style={{ animationDelay: "0ms" }}
                    />
                    <span
                      className="w-2 h-2 bg-primary/70 rounded-full animate-bounce"
                      style={{ animationDelay: "150ms" }}
                    />
                    <span
                      className="w-2 h-2 bg-primary/70 rounded-full animate-bounce"
                      style={{ animationDelay: "300ms" }}
                    />
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} className="h-4" />
            </div>
          )}
        </div>
      </main>

      <div className="fixed bottom-0 left-0 right-0 z-50 p-4 pb-6 bg-gradient-to-t from-background via-background to-background/80 backdrop-blur-md border-t border-white/5">
        <div className="max-w-3xl mx-auto">
          <ChatInput onSend={handleSendMessage} isLoading={isLoading} />
        </div>
      </div>
    </div>
  )
}

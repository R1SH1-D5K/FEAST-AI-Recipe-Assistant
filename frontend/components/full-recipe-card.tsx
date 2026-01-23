"use client"

import { useState } from "react"
import { Clock, Users, Flame, ExternalLink, ChefHat, Check } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import type { Recipe } from "@/lib/types"

interface FullRecipeCardProps {
  recipe: Recipe
}

export function FullRecipeCard({ recipe }: FullRecipeCardProps) {
  const [checkedIngredients, setCheckedIngredients] = useState<Set<number>>(new Set())
  const [activeTab, setActiveTab] = useState<"ingredients" | "instructions" | "nutrition">("ingredients")

  const toggleIngredient = (index: number) => {
    setCheckedIngredients((prev) => {
      const next = new Set(prev)
      if (next.has(index)) {
        next.delete(index)
      } else {
        next.add(index)
      }
      return next
    })
  }

  const instructions = Array.isArray(recipe.instructions)
    ? recipe.instructions
    : recipe.instructions.split(/\n+/).filter(Boolean)

  return (
    <Card className="w-full max-w-[520px] overflow-hidden border-white/10 bg-[#12151a] shadow-xl shadow-black/30">
      <div className="relative aspect-[16/9] overflow-hidden flex-shrink-0">
        <img
          src={recipe.image_url || `/placeholder.svg?height=192&width=500&query=${encodeURIComponent(recipe.title)}`}
          alt={recipe.title}
          className="w-full h-full object-cover"
          loading="lazy"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-[#12151a] via-[#12151a]/60 to-transparent" />
        <div className="absolute bottom-0 left-0 right-0 p-5">
          <h3 className="text-xl font-heading font-bold text-foreground text-balance mb-3 leading-tight">{recipe.title}</h3>
          <div className="flex flex-wrap gap-2">
            {recipe.cuisine && <Badge className="bg-primary/20 text-primary border-0 font-medium">{recipe.cuisine}</Badge>}
            {recipe.tags?.slice(0, 2).map((tag) => (
              <Badge key={tag} variant="outline" className="border-white/10 text-muted-foreground bg-white/5">
                {tag}
              </Badge>
            ))}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-6 px-5 py-3 border-b border-white/5 bg-white/5">
        {recipe.cooking_time && (
          <div className="flex items-center gap-2 text-sm">
            <Clock className="w-4 h-4 text-primary" />
            <span className="text-foreground/90">{recipe.cooking_time} min</span>
          </div>
        )}
        {recipe.servings && (
          <div className="flex items-center gap-2 text-sm">
            <Users className="w-4 h-4 text-primary" />
            <span className="text-foreground/90">{recipe.servings} servings</span>
          </div>
        )}
        {recipe.nutrition?.calories && (
          <div className="flex items-center gap-2 text-sm">
            <Flame className="w-4 h-4 text-primary" />
            <span className="text-foreground/90">{recipe.nutrition.calories} cal</span>
          </div>
        )}
      </div>

      <div className="flex gap-1 px-4 pt-3 border-b border-white/5">
        {(["ingredients", "instructions", "nutrition"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2.5 text-sm font-medium rounded-t-lg transition-all duration-200 ${
              activeTab === tab 
                ? "bg-white/10 text-foreground border-b-2 border-primary" 
                : "text-muted-foreground hover:text-foreground hover:bg-white/5"
            }`}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      <CardContent className="p-4 h-[280px] overflow-y-auto scrollbar-thin">
        {activeTab === "ingredients" && (
          <div className="space-y-2">
            {recipe.ingredients.map((ingredient, index) => (
              <button
                key={index}
                onClick={() => toggleIngredient(index)}
                className={`w-full flex items-center gap-3 p-3 rounded-xl bg-white/5 hover:bg-white/10 transition-all duration-200 text-left ${
                  checkedIngredients.has(index) ? "opacity-50" : ""
                }`}
              >
                <div
                  className={`w-5 h-5 rounded-md border-2 flex items-center justify-center transition-colors ${
                    checkedIngredients.has(index) ? "bg-primary border-primary" : "border-border"
                  }`}
                >
                  {checkedIngredients.has(index) && <Check className="w-3 h-3 text-primary-foreground" />}
                </div>
                <span
                  className={`text-sm ${checkedIngredients.has(index) ? "line-through text-muted-foreground" : ""}`}
                >
                  {ingredient.original || `${ingredient.quantity} ${ingredient.unit} ${ingredient.name}`}
                </span>
              </button>
            ))}
            {recipe.missing_ingredients && recipe.missing_ingredients.length > 0 && (
              <div className="mt-4 p-3 rounded-lg bg-destructive/10 border border-destructive/20">
                <p className="text-sm font-medium text-destructive mb-2">Missing Ingredients:</p>
                <ul className="text-sm text-muted-foreground space-y-1">
                  {recipe.missing_ingredients.map((item, i) => (
                    <li key={i}>• {item}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {activeTab === "instructions" && (
          <div className="space-y-4">
            {instructions.map((step, index) => (
              <div key={index} className="flex gap-4">
                <div className="w-7 h-7 rounded-full bg-primary/20 text-primary flex items-center justify-center text-sm font-bold shrink-0">
                  {index + 1}
                </div>
                <p className="text-sm text-foreground/90 pt-1 leading-relaxed">{step}</p>
              </div>
            ))}
          </div>
        )}

        {activeTab === "nutrition" && (
          <>
            {recipe.nutrition ? (
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                <NutritionItem label="Calories" value={recipe.nutrition.calories} unit="kcal" />
                <NutritionItem label="Protein" value={recipe.nutrition.protein} unit="g" />
                <NutritionItem label="Carbs" value={recipe.nutrition.carbs} unit="g" />
                <NutritionItem label="Fat" value={recipe.nutrition.fat} unit="g" />
                {recipe.nutrition.fiber && <NutritionItem label="Fiber" value={recipe.nutrition.fiber} unit="g" />}
                {recipe.nutrition.sugar && <NutritionItem label="Sugar" value={recipe.nutrition.sugar} unit="g" />}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
                <ChefHat className="w-10 h-10 mb-3 opacity-30" />
                <p className="text-sm">Nutrition info not available</p>
              </div>
            )}
          </>
        )}
      </CardContent>

      {recipe.source_url && (
        <div className="px-4 pb-4">
          <Button variant="outline" className="w-full bg-transparent border-border" asChild>
            <a href={recipe.source_url} target="_blank" rel="noopener noreferrer">
              <ExternalLink className="w-4 h-4 mr-2" />
              View Original Recipe
            </a>
          </Button>
        </div>
      )}
    </Card>
  )
}

function NutritionItem({ label, value, unit }: { label: string; value: number; unit: string }) {
  return (
    <div className="p-3 rounded-xl bg-muted/30 text-center">
      <p className="text-xl font-heading font-bold text-foreground">{value}</p>
      <p className="text-xs text-muted-foreground">
        {unit} {label}
      </p>
    </div>
  )
}

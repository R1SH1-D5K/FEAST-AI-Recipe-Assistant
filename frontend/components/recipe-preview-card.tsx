"use client"

import { Clock, Flame, ArrowRight } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import type { RecipePreview } from "@/lib/types"

interface RecipePreviewCardProps {
  preview: RecipePreview
  onClick: () => void
}

export function RecipePreviewCard({ preview, onClick }: RecipePreviewCardProps) {
  return (
    <Card
      className="overflow-hidden cursor-pointer group border-white/10 bg-[#12151a] hover:border-primary/50 hover:bg-[#181c23] transition-all duration-300 shadow-md shadow-black/20 hover:shadow-lg hover:shadow-black/30"
      onClick={onClick}
    >
      <div className="relative aspect-[16/10] overflow-hidden">
        <img
          src={preview.image_url || `/placeholder.svg?height=112&width=256&query=${encodeURIComponent(preview.title)}`}
          alt={preview.title}
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
          loading="lazy"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-[#12151a] via-transparent to-transparent" />
      </div>

      <CardContent className="p-4">
        <h3 className="font-heading font-semibold text-foreground text-sm mb-2 line-clamp-2 group-hover:text-primary transition-colors leading-tight">
          {preview.title}
        </h3>

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            {preview.cooking_time && (
              <span className="flex items-center gap-1">
                <Clock className="w-3.5 h-3.5" />
                {preview.cooking_time}m
              </span>
            )}
            {preview.nutrition?.calories && (
              <span className="flex items-center gap-1">
                <Flame className="w-3.5 h-3.5" />
                {preview.nutrition.calories} cal
              </span>
            )}
          </div>

          <span className="text-xs text-primary flex items-center gap-1 font-medium opacity-0 group-hover:opacity-100 transition-opacity duration-200">
            View
            <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
          </span>
        </div>

        {preview.cuisine && (
          <Badge variant="outline" className="text-xs mt-3 border-white/10 bg-white/5">
            {preview.cuisine}
          </Badge>
        )}
      </CardContent>
    </Card>
  )
}

from __future__ import annotations

import random

# Hand-picked: Marcus Aurelius, Epictetus, Seneca. Trimmed to fit a 32-char line.
QUOTES: list[tuple[str, str]] = [
    ("You have power over your mind — not outside events. Realize this, and you will find strength.", "Marcus Aurelius"),
    ("Waste no more time arguing what a good man should be. Be one.", "Marcus Aurelius"),
    ("The happiness of your life depends upon the quality of your thoughts.", "Marcus Aurelius"),
    ("If it is not right, do not do it; if it is not true, do not say it.", "Marcus Aurelius"),
    ("Confine yourself to the present.", "Marcus Aurelius"),
    ("The best revenge is to be unlike him who performed the injury.", "Marcus Aurelius"),
    ("Begin at once to live, and count each separate day as a separate life.", "Seneca"),
    ("Luck is what happens when preparation meets opportunity.", "Seneca"),
    ("We suffer more often in imagination than in reality.", "Seneca"),
    ("Difficulties strengthen the mind, as labor does the body.", "Seneca"),
    ("It is not the man who has too little, but the man who craves more, that is poor.", "Seneca"),
    ("As long as you live, keep learning how to live.", "Seneca"),
    ("First say to yourself what you would be; and then do what you have to do.", "Epictetus"),
    ("It is impossible for a man to learn what he thinks he already knows.", "Epictetus"),
    ("No man is free who is not master of himself.", "Epictetus"),
    ("Wealth consists not in having great possessions, but in having few wants.", "Epictetus"),
    ("Don't explain your philosophy. Embody it.", "Epictetus"),
    ("Make the best use of what is in your power, and take the rest as it happens.", "Epictetus"),
    ("He who laughs at himself never runs out of things to laugh at.", "Epictetus"),
    ("Circumstances don't make the man; they only reveal him to himself.", "Epictetus"),
    ("The whole future lies in uncertainty: live immediately.", "Seneca"),
    ("How does it help to make troubles heavier by bemoaning them?", "Seneca"),
    ("A gem cannot be polished without friction, nor a man perfected without trials.", "Seneca"),
    ("If you wish to improve, be content to appear clueless or stupid in extraneous matters.", "Epictetus"),
    ("Don't seek for everything to happen as you wish it would, but rather wish that everything happens as it actually will.", "Epictetus"),
    ("Caretake this moment.", "Epictetus"),
    ("The impediment to action advances action. What stands in the way becomes the way.", "Marcus Aurelius"),
    ("Dwell on the beauty of life. Watch the stars, and see yourself running with them.", "Marcus Aurelius"),
    ("Very little is needed to make a happy life; it is all within yourself, in your way of thinking.", "Marcus Aurelius"),
    ("How much trouble he avoids who does not look to see what his neighbour says or does or thinks.", "Marcus Aurelius"),
    ("Receive without conceit, release without struggle.", "Marcus Aurelius"),
    ("The first rule is to keep an untroubled spirit. The second is to look things in the face and know them for what they are.", "Marcus Aurelius"),
    ("It is the power of the mind to be unconquerable.", "Seneca"),
    ("True happiness is to enjoy the present, without anxious dependence upon the future.", "Seneca"),
    ("He suffers more than necessary, who suffers before it is necessary.", "Seneca"),
    ("Sometimes even to live is an act of courage.", "Seneca"),
    ("Hang on to your youthful enthusiasms — you'll be able to use them better when you're older.", "Seneca"),
    ("Every new beginning comes from some other beginning's end.", "Seneca"),
    ("All cruelty springs from weakness.", "Seneca"),
    ("Until we have begun to go without them, we fail to realize how unnecessary many things are.", "Seneca"),
    ("Things which you do not hope happen more frequently than things which you do hope.", "Plautus, via Seneca"),
    ("Don't demand or expect that events happen as you would wish them to.", "Epictetus"),
    ("Freedom is the only worthy goal in life. It is won by disregarding things that lie beyond our control.", "Epictetus"),
    ("People are not disturbed by things, but by the views they take of them.", "Epictetus"),
    ("First learn the meaning of what you say, and then speak.", "Epictetus"),
    ("Any person capable of angering you becomes your master.", "Epictetus"),
    ("Wealth is not how much you have; it is how much you can do without.", "Marcus Aurelius"),
    ("Reject your sense of injury and the injury itself disappears.", "Marcus Aurelius"),
    ("Be tolerant with others and strict with yourself.", "Marcus Aurelius"),
    ("If you are pained by any external thing, it is not this thing that disturbs you, but your own judgment about it.", "Marcus Aurelius"),
]


async def fetch() -> dict:
    text, author = random.choice(QUOTES)
    return {"text": text, "author": author}
